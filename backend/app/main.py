"""E&J's CHICKENS — FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging_config import configure_logging, get_logger
from app.db.session import engine
from app.routers import (
    activity,
    auth,
    birds,
    dashboard,
    expenses,
    feed,
    finance,
    health,
    mortality,
    notifications,
    reports,
    sales,
    settings as settings_router,
    users,
)

configure_logging()
logger = get_logger(__name__)

DESCRIPTION = """
Poultry farm management API for **E&J's CHICKENS**.

Every figure the application displays — bird populations, feed stock, expenses,
revenue, budget balance and profit or loss — is derived from recorded
transactions. Nothing is stored as a pre-computed summary.

**Getting started**

1. `POST /api/v1/auth/login` with your email/username and password.
2. Send the returned `access_token` as `Authorization: Bearer <token>`.
3. Try `GET /api/v1/dashboard/summary`.

**Roles** — `ADMIN` (everything), `MANAGER` (farm operations and finance),
`STAFF` (day-to-day recording).
"""


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate_for_runtime()
    if settings.uses_default_secret:
        logger.warning(
            "JWT_SECRET_KEY is still the default development value. "
            "Set a long random key in .env before deploying."
        )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection verified.")
    except Exception:  # pragma: no cover - startup diagnostics
        logger.exception(
            "Could not reach the database. Check DATABASE_URL in your .env file."
        )
    yield
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description=DESCRIPTION,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
    contact={"name": "E&J's CHICKENS"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

register_exception_handlers(app)

for router in (
    auth.router,
    users.router,
    dashboard.router,
    birds.router,
    mortality.router,
    health.router,
    feed.router,
    expenses.router,
    sales.router,
    finance.router,
    reports.router,
    notifications.router,
    activity.router,
    settings_router.router,
):
    app.include_router(router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["System"], summary="Service banner")
def root():
    return {
        "name": settings.APP_NAME,
        "version": "1.0.0",
        "environment": settings.APP_ENV,
        "documentation": "/docs",
        "api": settings.API_V1_PREFIX,
    }


@app.get("/health", tags=["System"], summary="Health check including the database")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database = "connected"
    except Exception:
        logger.exception("Health check could not reach the database.")
        database = "unavailable"
    return {"status": "ok" if database == "connected" else "degraded", "database": database}
