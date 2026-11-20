"""Main FastAPI application entry point for Society Cart backend.

Exposes authentication, user management, and society APIs with CORS configuration.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, societies, users, chat, rounds, orders, shopping_list
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo
from app.services import order_service
from app.services.round_scheduler import start_round_scheduler, stop_round_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: connect to MongoDB, start scheduler on startup, close on shutdown."""
    await connect_to_mongo()
    start_round_scheduler()
    # Trigger automatic background recovery for any interrupted orders on startup using safe timeout threshold
    asyncio.create_task(order_service.recover_stale_processing_orders(timeout_seconds=120))
    yield
    stop_round_scheduler()
    await close_mongo_connection()


app = FastAPI(
    title="Society Cart API",
    description="Community-based group grocery ordering platform for apartment societies.",
    version="0.2.0",
    lifespan=lifespan,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth.router, prefix="/api")
app.include_router(users.router, prefix="/api")
app.include_router(societies.router, prefix="/api")
app.include_router(rounds.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(shopping_list.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def get_root() -> Dict[str, str]:
    """Root endpoint returning basic service status."""
    return {
        "message": "Society Cart API is running",
        "status": "healthy",
    }


@app.get("/health")
def get_health() -> Dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
    }
