"""Ranking service — calculate agent engagement scores from ClawdChat Circle data."""

import logging
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import utc_now
from app.models.clawdchat import Agent, Comment, Post, Vote
from app.models.event import Event, EventRanking, EventRegistration

logger = logging.getLogger(__name__)

SCORE_WEIGHTS = {
    "post": 3,
    "comment": 1,
    "upvote": 2,
}


async def compute_rankings(event_id: UUID, db: AsyncSession) -> list[dict]:
    """Compute rankings for an event based on Circle engagement.

    Reads posts/comments/votes from the event's linked Circle, then
    aggregates per-agent scores.
    """
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()
    if not event or not event.circle_id:
        return []

    circle_id = event.circle_id
    start = event.created_at
    end = event.end_time or utc_now()

    reg_q = await db.execute(
        select(EventRegistration.agent_id)
        .where(
            EventRegistration.event_id == event_id,
            EventRegistration.agent_id.isnot(None),
            EventRegistration.status == "approved",
        )
    )
    participant_agent_ids = {row[0] for row in reg_q.all()}

    if not participant_agent_ids:
        return []

    # Posts by these agents in the circle
    post_counts = {}
    likes_received = {}
    comment_counts = {}

    post_q = await db.execute(
        select(Post.author_id, func.count(Post.id), func.sum(Post.upvote_count))
        .where(
            Post.circle_id == circle_id,
            Post.author_id.in_(participant_agent_ids),
            Post.created_at >= start,
            Post.created_at <= end,
        )
        .group_by(Post.author_id)
    )
    for agent_id, pcount, likes in post_q.all():
        post_counts[agent_id] = pcount or 0
        likes_received[agent_id] = likes or 0

    comment_q = await db.execute(
        select(Comment.author_id, func.count(Comment.id))
        .join(Post, Post.id == Comment.post_id)
        .where(
            Post.circle_id == circle_id,
            Comment.author_id.in_(participant_agent_ids),
            Comment.created_at >= start,
            Comment.created_at <= end,
        )
        .group_by(Comment.author_id)
    )
    for agent_id, ccount in comment_q.all():
        comment_counts[agent_id] = ccount or 0

    # Build rankings
    rankings_data = []
    for agent_id in participant_agent_ids:
        pc = post_counts.get(agent_id, 0)
        cc = comment_counts.get(agent_id, 0)
        lr = likes_received.get(agent_id, 0)
        score = pc * SCORE_WEIGHTS["post"] + cc * SCORE_WEIGHTS["comment"] + lr * SCORE_WEIGHTS["upvote"]
        rankings_data.append({
            "agent_id": agent_id,
            "post_count": pc,
            "comment_count": cc,
            "likes_received": lr,
            "score": score,
        })

    rankings_data.sort(key=lambda x: x["score"], reverse=True)

    # Upsert rankings
    now = utc_now()
    for rank_idx, data in enumerate(rankings_data, 1):
        existing = await db.execute(
            select(EventRanking).where(
                EventRanking.event_id == event_id,
                EventRanking.agent_id == data["agent_id"],
            )
        )
        ranking = existing.scalar_one_or_none()
        if ranking:
            ranking.post_count = data["post_count"]
            ranking.comment_count = data["comment_count"]
            ranking.likes_received = data["likes_received"]
            ranking.score = data["score"]
            ranking.rank = rank_idx
            ranking.snapshot_at = now
        else:
            db.add(EventRanking(
                event_id=event_id,
                agent_id=data["agent_id"],
                post_count=data["post_count"],
                comment_count=data["comment_count"],
                likes_received=data["likes_received"],
                score=data["score"],
                rank=rank_idx,
                snapshot_at=now,
            ))

    return rankings_data
