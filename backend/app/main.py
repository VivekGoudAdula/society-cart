"""Main FastAPI application entry point for Society Cart backend.

Exposes minimal root and health check endpoints with CORS configuration.
"""

from typing import Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Society Cart API",
    description="Community-based group grocery ordering platform for apartment societies.",
    version="0.1.0",
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def get_root() -> Dict[str, str]:
    """Root endpoint returning basic service status.

    Returns:
        Dict[str, str]: Service running message and health status.
    """
    return {
        "message": "Society Cart API is running",
        "status": "healthy",
    }


@app.get("/health")
def get_health() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict[str, str]: Simple health check response.
    """
    return {
        "status": "healthy",
    }
