import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import get_settings
from src.database import init_db
from src.api.router import api_router
from src.api.health import router as health_router
from src.vapi.client import sync_vapi_webhook_on_startup
from src.llm.openrouter import close_shared_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_db()

    # Sync VAPI webhook URL automatically
    # This ensures VAPI sends webhooks to the correct URL (ngrok in dev)
    logger.info("Syncing VAPI webhook URL...")
    await sync_vapi_webhook_on_startup()

    yield
    # Shutdown
    logger.info("Shutting down application...")
    await close_shared_client()  # Clean up HTTP connection pool


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Voice-first longitudinal clinical decision support system for mental health",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "docs": "/docs",
    }
