import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings, get_settings
from app.database import engine
from app.routers import audit_events, auth, categories, expenses, inventory, products, purchasing, reports, returns, sales, users


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    docs = settings.api_docs_enabled
    application = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs" if docs else None,
                          redoc_url="/redoc" if docs else None, openapi_url="/openapi.json" if docs else None)
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    application.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True,
                               allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                               allow_headers=["Content-Type", "Accept"])

    @application.middleware("http")
    async def production_security(request: Request, call_next):
        started = time.monotonic()
        if settings.app_env == "production" and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            allowed = set(settings.trusted_origins or settings.cors_origins)
            if origin and origin not in allowed:
                return JSONResponse({"detail": "Untrusted request origin"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        if settings.app_env == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Server-Timing"] = f'app;dur={(time.monotonic() - started) * 1000:.1f}'
        return response

    for router in (categories.router, products.router, sales.router, inventory.router, reports.router,
                   purchasing.router, returns.router, expenses.router, auth.router, users.router, audit_events.router):
        application.include_router(router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "stockflow-api"}

    @application.get("/ready", tags=["system"])
    def ready():
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)
        return {"status": "ready"}

    # An explicit API fallback prevents the SPA from hiding API route mistakes.
    @application.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
    def api_not_found(path: str):
        raise HTTPException(404, "Not Found")

    dist = Path(settings.frontend_dist_dir) if settings.frontend_dist_dir else Path(__file__).parent / "static"
    if dist.joinpath("index.html").is_file():
        @application.get("/assets/{path:path}", include_in_schema=False)
        def static_asset(path: str):
            candidate = (dist / "assets" / path).resolve()
            if not candidate.is_relative_to((dist / "assets").resolve()) or not candidate.is_file():
                raise HTTPException(404, "Not Found")
            return FileResponse(candidate, headers={"Cache-Control": "public, max-age=31536000, immutable"})

        if not docs:
            @application.get("/{disabled_path:path}", include_in_schema=False)
            def disabled_docs(disabled_path: str):
                if disabled_path in {"docs", "redoc", "openapi.json"}:
                    raise HTTPException(404, "Not Found")
                return spa_response(disabled_path)

        def spa_response(path: str):
            candidate = (dist / path).resolve()
            if path and candidate.is_relative_to(dist.resolve()) and candidate.is_file():
                return FileResponse(candidate, headers={"Cache-Control": "public, max-age=31536000, immutable"})
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

        if docs:
            @application.get("/{path:path}", include_in_schema=False)
            def spa(path: str):
                return spa_response(path)

    return application


app = create_app()
