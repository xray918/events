"""Database session — connects to the shared ClawdChat PostgreSQL."""

from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Create only event_* tables (never touch ClawdChat tables)."""
    from app.models import clawdchat, event  # noqa: F401 — register models

    async with engine.begin() as conn:
        await conn.run_sync(
            Base.metadata.create_all,
            tables=[
                t for t in Base.metadata.sorted_tables
                if t.name.startswith("event_") or t.name.startswith("sms_")
            ],
        )
        # Incremental migrations for existing tables (safe to re-run)
        from sqlalchemy import text
        await conn.execute(text(
            "ALTER TABLE event_events ADD COLUMN IF NOT EXISTS clawdchat_post_id UUID"
        ))
        await conn.execute(text(
            "ALTER TABLE event_events ADD COLUMN IF NOT EXISTS organizer_name VARCHAR(200)"
        ))
