"""Root entry point for Render/cloud deployments running from repository root."""
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_path = Path(__file__).resolve().parent / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.main import app  # noqa: E402

__all__ = ["app"]
