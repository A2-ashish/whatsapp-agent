"""
WhatsApp Commerce Platform — FastAPI Application Entry Point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db.database import engine
from app.db.models import Base

# Import all routers
from app.api.webhook import router as webhook_router
from app.api.dashboard.auth import router as auth_router
from app.api.dashboard.inventory import router as inventory_router
from app.api.dashboard.orders import router as orders_router
from app.api.dashboard.escalations import router as escalations_router
from app.api.dashboard.policies import router as policies_router
from app.api.dashboard.conversations import router as conversations_router
from app.api.dashboard.analytics import router as analytics_router
from app.api.dashboard.sse import router as sse_router

settings = get_settings()

# Logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info(f"Starting {settings.APP_NAME}")

    # Create tables (dev mode — use Alembic migrations in production)
    if settings.DEBUG:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified")

    yield

    # Shutdown
    from app.whatsapp.client import whatsapp_client
    await whatsapp_client.close()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title=settings.APP_NAME,
    description="Agentic WhatsApp Commerce Platform for Small Retailers/Wholesalers",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow dashboard frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
app.include_router(webhook_router, prefix="")
app.include_router(auth_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(escalations_router, prefix="/api")
app.include_router(policies_router, prefix="/api")
app.include_router(conversations_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(sse_router, prefix="/api")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME}
