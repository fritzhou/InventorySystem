from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import audit_events, auth, categories, expenses, inventory, products, reports, returns, sales, purchasing, users

settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(categories.router)
app.include_router(products.router)
app.include_router(sales.router)
app.include_router(inventory.router)
app.include_router(reports.router)
app.include_router(purchasing.router)
app.include_router(returns.router)
app.include_router(expenses.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit_events.router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "stockflow-api"}
