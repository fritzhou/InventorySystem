from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import Engine, text
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.core.config import Settings, get_settings
from app.database import engine as shared_engine
from app.routers import audit_events, auth, categories, expenses, inventory, products, purchasing, reports, returns, sales, users

ROUTERS = (categories, products, sales, inventory, reports, purchasing, returns, expenses, auth, users, audit_events)
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def create_app(settings: Settings | None = None, engine: Engine | None = None) -> FastAPI:
    cfg = settings or get_settings()
    db_engine = engine or shared_engine
    docs = {} if cfg.docs_enabled else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    application = FastAPI(title=cfg.app_name, version="0.1.0", **docs)
    application.state.engine = db_engine
    application.state.settings = cfg
    application.add_middleware(TrustedHostMiddleware, allowed_hosts=cfg.allowed_hosts)
    application.add_middleware(CORSMiddleware, allow_origins=cfg.cors_origins, allow_credentials=True,
                               allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                               allow_headers=["Authorization", "Content-Type"])

    @application.middleware("http")
    async def production_security(request: Request, call_next):
        started = monotonic()
        if cfg.app_env == "production" and request.url.path.startswith("/api/") and request.method in UNSAFE_METHODS:
            candidate = request.headers.get("origin")
            if not candidate:
                referer = request.headers.get("referer")
                candidate = f"{urlsplit(referer).scheme}://{urlsplit(referer).netloc}" if referer else None
            if candidate not in cfg.trusted_origins:
                return JSONResponse({"detail": "Request origin is not trusted"}, status_code=403)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if cfg.app_env == "production" and cfg.session_cookie_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Server-Timing"] = f"app;dur={(monotonic() - started) * 1000:.1f}"
        return response

    for router in ROUTERS:
        application.include_router(router.router)

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "stockflow-api"}

    @application.get("/ready", tags=["system"])
    def ready():
        try:
            with application.state.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return {"status": "ready"}
        except Exception:
            return JSONResponse({"status": "unavailable"}, status_code=503)

    dist = Path(cfg.frontend_dist_dir).resolve()
    if dist.is_dir() and (dist / "index.html").is_file():
        @application.get("/{spa_path:path}", include_in_schema=False)
        def spa(spa_path: str):
            requested = (dist / spa_path).resolve()
            if spa_path.startswith("api/"):
                return JSONResponse({"detail": "Not Found"}, status_code=404)
            if requested.is_relative_to(dist) and requested.is_file():
                cache = "public, max-age=31536000, immutable" if spa_path.startswith("assets/") else "no-store"
                return FileResponse(requested, headers={"Cache-Control": cache})
            return FileResponse(dist / "index.html", headers={"Cache-Control": "no-store"})
    return application


app = create_app()
