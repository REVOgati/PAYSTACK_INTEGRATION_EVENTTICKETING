from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import get_settings
from app.database import engine

settings =get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ───────────────────────────────────────────────────
    async with engine.connect() as conn:
        await conn.run_sync(lambda _: None)
    print("Database connection established")
    yield
    # ── Shutdown ──────────────────────────────────────────────────
    await engine.dispose()
    print("Database connection closed")

app = FastAPI(
    title="Blue tickets API",
    description = "Event ticketing API with paystack payment integration",
    version = "0.1.0",
    lifespan=lifespan
)

@app.get("/health")
async def health_check():
    return {"status": "ok",
            "environment": settings.APP_ENV,
            "message": "API is healthy and running"}