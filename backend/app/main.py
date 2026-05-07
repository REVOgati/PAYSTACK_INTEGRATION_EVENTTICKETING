from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.database import engine
from app.routers.auth import router as auth_router
from app.routers.events import router as events_router
from app.routers.bookings import router as bookings_router
from app.routers.payments import router as payments_router
from app.routers.webhooks import router as webhooks_router
from app.utils.logging_config import setup_logging, add_exception_handlers

logger = setup_logging()
settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    async with engine.connect() as conn:
        await conn.run_sync(lambda _: None)
    logger.info("Database connection established")
    yield
    # ── Shutdown ──────────────────────────────────────────────────
    await engine.dispose()
    logger.info("Database connection closed")

app = FastAPI(
    title="Blue tickets API",
    description = "Event ticketing API with paystack payment integration",
    version = "0.1.0",
    lifespan=lifespan
)

add_exception_handlers(app)

app.include_router(auth_router)
app.include_router(events_router)
app.include_router(bookings_router)
app.include_router(payments_router)
app.include_router(webhooks_router)

@app.get("/health")
async def health_check():
    return {"status": "ok",
            "environment": settings.APP_ENV,
            "message": "API is healthy and running"}