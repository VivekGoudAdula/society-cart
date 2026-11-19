"""Main FastAPI application entry point for Society Cart backend.

Exposes authentication, user management, and society APIs with CORS configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, societies, users, chat
from app.core.config import get_settings
from app.core.database import close_mongo_connection, connect_to_mongo

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Manage application lifespan: connect to MongoDB on startup, close on shutdown."""
    await connect_to_mongo()
    yield
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
