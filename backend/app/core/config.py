"""Application configuration module.

Loads environment variables using Pydantic Settings with sensible defaults.
"""

from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

_env_file = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings schema backed by environment variables."""

    model_config = SettingsConfigDict(
        env_file=str(_env_file) if _env_file.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    frontend_origin: str = "http://localhost:5173"

    mongodb_uri: str = ""
    mongodb_database: str = "society_cart"

    # JWT Authentication settings
    jwt_secret_key: str = "society_cart_dev_jwt_secret_change_in_production_key_2026"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # Cookie security settings
    cookie_secure: bool = False
    cookie_samesite: str = "lax"

    # External APIs (Nexconn, Groq)
    nexconn_app_key: str = ""
    nexconn_app_secret: str = ""
    nexconn_api_base_url: str = "https://api-sg01.ronghub.com"
    groq_api_key: str = ""

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env.lower() in ("production", "prod")

    @property
    def cors_origins(self) -> List[str]:
        """Return allowed CORS origins based on configuration."""
        origins = [self.frontend_origin]
        if "localhost" in self.frontend_origin:
            origins.append(self.frontend_origin.replace("localhost", "127.0.0.1"))
        return list(dict.fromkeys(origins))


def get_settings() -> Settings:
    """Instantiate and return application settings."""
    return Settings()
