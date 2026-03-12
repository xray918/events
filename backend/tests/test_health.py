"""Basic health and root tests."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "Events"


@pytest.mark.asyncio
async def test_root(client: AsyncClient):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["service"] == "Events"
    assert "/docs" == data["docs"]


@pytest.mark.asyncio
async def test_skill_md(client: AsyncClient):
    resp = await client.get("/skill.md")
    assert resp.status_code == 200
    assert "Events" in resp.text


@pytest.mark.asyncio
async def test_staff_skill_md(client: AsyncClient):
    resp = await client.get("/staff-skill.md")
    assert resp.status_code == 200
    assert "Staff" in resp.text


@pytest.mark.asyncio
async def test_api_docs_section(client: AsyncClient):
    resp = await client.get("/api-docs/events")
    assert resp.status_code == 200
    assert "Events API" in resp.text

    resp = await client.get("/api-docs/nonexistent")
    assert resp.status_code == 200
    assert "not found" in resp.text
