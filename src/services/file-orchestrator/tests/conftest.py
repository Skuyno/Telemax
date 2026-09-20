"""Shared fixtures for file-orchestrator tests."""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.database import Base
from app.dependencies import get_async_db
from app.main import app

TEST_DATABASE_URL = (
    "postgresql+asyncpg://postgres:mysecretpassword@localhost:5430/"
    "test_telemax_file_orchestrator"
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
test_session_maker = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(autouse=True)
def mock_communication_service():
    """Mock the membership check made against communication's internal API."""
    with patch("app.files.service.httpx.AsyncClient") as mock_client_class:
        mock_client_instance = AsyncMock()
        mock_client_class.return_value = mock_client_instance
        mock_client_instance.__aenter__.return_value = mock_client_instance

        def _fake_get(url, *args, **kwargs):
            response = AsyncMock()
            response.raise_for_status = lambda: None
            if url.endswith("/members"):
                response.json = lambda: {"user_ids": []}
            else:
                response.json = lambda: {"is_member": True}
            return response

        mock_client_instance.get.side_effect = _fake_get

        yield mock_client_class


@pytest.fixture(autouse=True)
def mock_storage():
    """Mock SeaweedFS storage calls: unlimited free space, in-memory blobs."""
    blobs: dict[str, bytes] = {}

    async def _get_free_bytes():
        return 10_000_000_000

    async def _put_object(storage_key, content_type, body):
        chunks = bytearray()
        async for chunk in body:
            chunks.extend(chunk)
        blobs[storage_key] = bytes(chunks)

    async def _delete_object(storage_key):
        blobs.pop(storage_key, None)

    async def _stream_object(storage_key):
        data = blobs[storage_key]

        async def _body():
            yield data

        return _body(), "application/octet-stream"

    with (
        patch("app.files.service.storage.get_free_bytes", _get_free_bytes),
        patch("app.files.service.storage.put_object", _put_object),
        patch("app.files.service.storage.delete_object", _delete_object),
        patch("app.files.service.storage.stream_object", _stream_object),
    ):
        yield blobs


@pytest.fixture(autouse=True)
def mock_nats_client():
    """Mock NATS client publish method for all tests."""
    with patch("app.events.nats_client.publish") as mock_publish:
        yield mock_publish


@pytest.fixture(scope="session")
def create_models():
    """Create tables in the test database once per test run."""

    async def _create():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create())


@pytest.fixture
async def client(create_models):
    """HTTP client wired to the app with the test database."""

    async def override_get_db():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_async_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE files CASCADE"))

    app.dependency_overrides.clear()
