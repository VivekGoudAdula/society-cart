"""Application configuration module.

Loads environment variables using Pydantic Settings with sensible defaults.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings schema backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    mongodb_uri: str = ""
    mongodb_database: str = "society_cart"

    nexconn_app_key: str = ""
    nexconn_app_secret: str = ""
    nexconn_api_base_url: str = ""

    groq_api_key: str = ""

    @property
    def cors_origins(self) -> List[str]:
        """Return allowed CORS origins based on configuration."""
        origins = [self.frontend_origin]
        # Allow localhost loopback variations for development convenience
        if "localhost" in self.frontend_origin:
            origins.append(self.frontend_origin.replace("localhost", "127.0.0.1"))
        return list(dict.fromkeys(origins))


def get_settings() -> Settings:
    """Instantiate and return application settings."""
    return Settings()
