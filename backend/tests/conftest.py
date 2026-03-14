"""Test fixtures — session-scoped event loop, isolated test database.

IMPORTANT: All tests run against a SEPARATE `events_test` database so that
test data never contaminates the development / production `clawdchat` database.

The test database is created automatically if it doesn't exist.
All event tables are truncated both BEFORE and AFTER the test session.
"""

import asyncio
import os

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

# ─────────────────────────────────────────────────────────────────────────────
# Override DATABASE_URL to use the isolated test database.
# This MUST happen before any app modules are imported, because
# app/db/session.py creates the SQLAlchemy engine at module-load time using
# settings.database_url, and pydantic-settings gives env-vars priority over
# .env file values.
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_TEST_DB = (
    "postgresql+asyncpg://clawdchat:clawdchat123@localhost:5432/events_test"
)
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", _DEFAULT_TEST_DB)
os.environ["DATABASE_URL"] = _TEST_DB_URL


from main import app  # noqa: E402 — must be imported AFTER env override


# ─────────────────────────────────────────────────────────────────────────────
# Tables owned by this test suite (truncated before + after every session).
# Order: children before parents to avoid FK violations.
# ─────────────────────────────────────────────────────────────────────────────
_TEST_TABLES = [
    "event_blast_logs",
    "event_blasts",
    "event_feedbacks",
    "event_winners",
    "event_rankings",
    "event_cohosts",
    "event_staff",
    "event_registrations",
    "event_custom_questions",
    "event_events",
    "sms_logs",
    "sms_templates",
    "users",
    "agents",
]


async def _create_test_db_if_needed() -> None:
    """Create the `events_test` PostgreSQL database if it doesn't exist yet.

    Strategy: connect to the `clawdchat` database first to check existence,
    then use a subprocess `createdb` call (which uses OS-user peer auth and
    typically succeeds even when the app user lacks CREATEDB privilege).
    """
    import subprocess

    db_name = _TEST_DB_URL.rsplit("/", 1)[-1]
    try:
        import asyncpg

        # Parse connection details from the URL
        dsn_body = _TEST_DB_URL.replace("postgresql+asyncpg://", "")
        user_pass, rest = dsn_body.split("@", 1) if "@" in dsn_body else ("", dsn_body)
        host_port = rest.split("/", 1)[0]
        user, password = user_pass.split(":", 1) if ":" in user_pass else (user_pass, "")
        host, port = (host_port.split(":", 1) if ":" in host_port else (host_port, "5432"))

        # Connect to an existing database just to check whether events_test exists
        conn = await asyncpg.connect(
            host=host, port=int(port), user=user, password=password, database=user
        )
        try:
            exists = await conn.fetchval(
                "SELECT 1 FROM pg_database WHERE datname = $1", db_name
            )
        finally:
            await conn.close()

        if not exists:
            result = subprocess.run(
                ["createdb", "-O", user, db_name],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                print(f"\n  [conftest] Created test database: {db_name}")
            else:
                print(f"\n  [conftest] ⚠️  createdb failed: {result.stderr.strip()}")
                print(f"  Please create it manually:  createdb -O clawdchat {db_name}")
    except Exception as exc:
        print(f"\n  [conftest] ⚠️  Could not verify/create test database: {exc}")
        print(f"  Please create it manually:  createdb -O clawdchat {db_name}")


async def _truncate_test_tables(engine) -> None:
    """Truncate all event/user tables in the test database."""
    from sqlalchemy import text

    async with engine.begin() as conn:
        for table in _TEST_TABLES:
            try:
                await conn.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
            except Exception:
                pass  # table may not exist yet on first run


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole test session (avoids asyncpg pool issues)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """
    Session-scoped fixture that:
      1. Ensures the `events_test` database exists (creates it if needed).
      2. Creates ALL tables (including ClawdChat's `users` table for FK support).
      3. Truncates all test tables BEFORE tests start (stale data guard).
      4. Yields to run the test session.
      5. Truncates all test tables AFTER tests finish (restore to clean state).
    """
    await _create_test_db_if_needed()

    # Import after env override so the engine points to events_test
    from app.db.session import engine, Base
    from app.models import clawdchat, event  # noqa: F401 — register ORM metadata
    from sqlalchemy import text

    # Create ALL tables (users + all event_* tables)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Incremental columns (safe to re-run)
        await conn.execute(text(
            "ALTER TABLE event_events ADD COLUMN IF NOT EXISTS clawdchat_post_id UUID"
        ))
        await conn.execute(text(
            "ALTER TABLE event_events ADD COLUMN IF NOT EXISTS organizer_name VARCHAR(200)"
        ))

    # ── PRE-TEST CLEANUP (guard against leftovers from a previous crashed run) ──
    await _truncate_test_tables(engine)
    print("\n  [conftest] Test database ready (all tables clean).")

    yield  # ←── tests run here

    # ── POST-TEST CLEANUP (restore clean state so frontend stays tidy) ───────
    await _truncate_test_tables(engine)
    print("\n  [conftest] Test database cleaned up after session.")

    await engine.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
