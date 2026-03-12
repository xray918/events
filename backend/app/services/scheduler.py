"""Background scheduler — periodic tasks like auto-archiving expired events."""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.db.session import async_session
from app.models.event import Event

logger = logging.getLogger(__name__)

ARCHIVE_AFTER_DAYS = 3
CHECK_INTERVAL_SECONDS = 3600  # 1 hour


async def archive_expired_events():
    """Mark published events as 'completed' if they ended more than N days ago."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=ARCHIVE_AFTER_DAYS)

    async with async_session() as session:
        async with session.begin():
            stmt = (
                update(Event)
                .where(
                    Event.status == "published",
                    Event.end_time.isnot(None),
                    Event.end_time < cutoff,
                )
                .values(status="completed")
                .returning(Event.id)
            )
            result = await session.execute(stmt)
            archived_ids = [row[0] for row in result.all()]

            if archived_ids:
                logger.info(f"Auto-archived {len(archived_ids)} events: {archived_ids}")
            return len(archived_ids)


async def scheduler_loop():
    """Run periodic tasks in background."""
    logger.info(f"Scheduler started: archive check every {CHECK_INTERVAL_SECONDS}s, cutoff={ARCHIVE_AFTER_DAYS} days")
    while True:
        try:
            count = await archive_expired_events()
            if count:
                logger.info(f"Archived {count} expired events")
        except Exception as e:
            logger.error(f"Scheduler error: {e}", exc_info=True)
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)
