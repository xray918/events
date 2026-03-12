"""Test fixtures — session-scoped event loop for asyncpg compatibility."""

import asyncio

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app


@pytest.fixture(scope="session")
def event_loop():
    """Use a single event loop for all tests to avoid asyncpg pool issues."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
