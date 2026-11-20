"""Test configuration and fixtures for Phase 2 backend verification.
"""

import os
from pathlib import Path
import pytest
from dotenv import load_dotenv
from httpx import AsyncClient, ASGITransport

# Explicitly load backend .env
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
load_dotenv(env_path, override=True)

from app.core.config import get_settings
from app.core.database import connect_to_mongo, close_mongo_connection, get_database
from app.main import app

settings = get_settings()
TEST_DB_NAME = "society_cart_automated_tests"
settings.mongodb_database = TEST_DB_NAME
os.environ["MONGODB_DATABASE"] = TEST_DB_NAME


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Connect to test database and clean up before/after test suite."""
    db = await connect_to_mongo()
    if db is not None:
        try:
            # Clean collections prior to test run for clean test state
            await db.users.drop()
            await db.societies.drop()
            await db.memberships.drop()
            await db.order_rounds.drop()
            await db.grocery_submissions.drop()
            await db.grocery_orders.drop()
        except Exception:
            pass
    yield db
    if db is not None:
        try:
            await db.users.drop()
            await db.societies.drop()
            await db.memberships.drop()
            await db.order_rounds.drop()
            await db.grocery_submissions.drop()
            await db.grocery_orders.drop()
        except Exception:
            pass
    await close_mongo_connection()


@pytest.fixture
async def client():
    """Async test client bound to FastAPI application."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac
