"""ClawdChat API client — create Circles and post on behalf of agents."""

import logging
from typing import Optional
from uuid import UUID

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TIMEOUT = 15.0


async def _call_api(
    method: str,
    path: str,
    api_key: str,
    json_data: Optional[dict] = None,
) -> dict:
    url = f"{settings.clawdchat_api_base}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.request(method, url, headers=headers, json=json_data)
    if resp.status_code >= 400:
        logger.error(f"ClawdChat API {method} {path} → {resp.status_code}: {resp.text[:300]}")
    try:
        body = resp.json()
    except Exception:
        body = {}
    return {"status": resp.status_code, "data": body}


async def create_circle(
    name: str,
    description: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Create a Circle in ClawdChat. Returns circle data dict or None."""
    key = api_key or settings.events_bot_api_key
    if not key:
        logger.warning("No API key for Circle creation, skipping")
        return None

    result = await _call_api("POST", "/circles", key, {
        "name": name,
        "description": description,
    })

    if result["status"] == 201:
        circle = result["data"]
        logger.info(f"Circle created: {circle.get('name')} (id={circle.get('id')})")
        return circle

    logger.error(f"Failed to create circle '{name}': status={result['status']}, body={result['data']}")
    return None


async def create_post(
    circle_name: str,
    title: str,
    content: Optional[str] = None,
    url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Create a post in a ClawdChat Circle. Returns post data dict or None."""
    key = api_key or settings.events_bot_api_key
    if not key:
        logger.warning("No API key for posting, skipping")
        return None

    body: dict = {"circle": circle_name, "title": title}
    if content:
        body["content"] = content
    if url:
        body["url"] = url

    result = await _call_api("POST", "/posts", key, body)

    if result["status"] == 201:
        post = result["data"]
        logger.info(f"Post created in '{circle_name}': {title}")
        return post

    logger.error(f"Failed to post in '{circle_name}': status={result['status']}, body={result['data']}")
    return None


async def update_post(
    post_id: str,
    title: Optional[str] = None,
    content: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[dict]:
    """Update (PATCH) an existing ClawdChat post. Returns updated post data or None."""
    key = api_key or settings.events_bot_api_key
    if not key:
        logger.warning("No API key for post update, skipping")
        return None

    body: dict = {}
    if title:
        body["title"] = title
    if content:
        body["content"] = content
    if not body:
        return None

    result = await _call_api("PATCH", f"/posts/{post_id}", key, body)

    if result["status"] == 200:
        post = result["data"]
        logger.info(f"Post {post_id} updated")
        return post

    logger.error(f"Failed to update post {post_id}: status={result['status']}, body={result['data']}")
    return None


async def archive_circle(
    circle_name: str,
    api_key: Optional[str] = None,
) -> bool:
    """Archive a ClawdChat Circle (soft-delete): is_active=False, all posts is_deleted=True.
    Stats are preserved. Returns True on success or if already gone, False on error."""
    key = api_key or settings.events_bot_api_key
    if not key:
        logger.warning("No API key for Circle archival, skipping")
        return False

    result = await _call_api("POST", f"/circles/{circle_name}/archive", key)

    if result["status"] in (200, 404):
        if result["status"] == 404:
            logger.info(f"Circle '{circle_name}' not found, treating as already archived")
        else:
            logger.info(f"Circle '{circle_name}' archived")
        return True

    logger.error(f"Failed to archive circle '{circle_name}': status={result['status']}, body={result['data']}")
    return False


async def notify_event_cancelled(
    event_title: str,
    event_slug: str,
    circle_name: str,
    api_key: Optional[str] = None,
) -> None:
    """Post a cancellation notice to the event's ClawdChat Circle."""
    event_url = f"{settings.frontend_url}/e/{event_slug}"
    await create_post(
        circle_name=circle_name,
        title=f"❌ 活动已取消：{event_title}",
        content=(
            f"很遗憾，**{event_title}** 活动已被主办方取消。\n\n"
            f"感谢大家的关注与支持，期待下次再见！\n\n"
            f"活动详情：{event_url}"
        ),
        url=event_url,
        api_key=api_key,
    )


def build_event_post_content(
    event_title: str,
    event_description: Optional[str],
    event_slug: str,
) -> tuple[str, str]:
    """Build (title, content) for event announce post."""
    event_url = f"{settings.frontend_url}/e/{event_slug}"
    post_title = f"📢 活动发布：{event_title}"
    post_content = (
        f"📢 **{event_title}** 活动已发布！\n\n"
        f"{event_description or ''}\n\n"
        f"👉 报名链接：{event_url}\n\n"
        f"欢迎参加，期待与你相见！"
    )
    return post_title, post_content


async def publish_event_to_clawdchat(
    event_title: str,
    event_description: Optional[str],
    event_slug: str,
    agent_api_key: Optional[str] = None,
) -> Optional[tuple[UUID, str, Optional[UUID]]]:
    """Create a Circle + announce post for a published event.

    - If agent_api_key is provided (agent publishes), use that agent's key.
    - Otherwise (human publishes), use EventsBot's key.

    Returns (circle_uuid, circle_name_slug, post_uuid) or None if creation failed.
    """
    api_key = agent_api_key or settings.events_bot_api_key

    circle_display_name = f"🎉 {event_title}"
    circle_desc = (event_description or "")[:500]
    if circle_desc:
        circle_desc = f"活动圈子 — {circle_desc}"
    else:
        circle_desc = f"活动圈子 — {event_title}"

    circle = await create_circle(circle_display_name, circle_desc, api_key=api_key)

    if not circle:
        unique_name = f"🎉 {event_title} ({event_slug[-8:]})"
        circle = await create_circle(unique_name, circle_desc, api_key=api_key)
        if not circle:
            return None

    circle_id = circle.get("id")
    actual_circle_name = circle.get("name", circle_display_name)

    event_url = f"{settings.frontend_url}/e/{event_slug}"
    post_title, post_content = build_event_post_content(event_title, event_description, event_slug)

    post = await create_post(
        circle_name=actual_circle_name,
        title=post_title,
        content=post_content,
        url=event_url,
        api_key=api_key,
    )

    post_id: Optional[UUID] = None
    if post and post.get("id"):
        try:
            post_id = UUID(str(post["id"]))
        except (ValueError, TypeError):
            logger.warning(f"Invalid post_id from ClawdChat: {post.get('id')}")

    try:
        return UUID(str(circle_id)), actual_circle_name, post_id
    except (ValueError, TypeError):
        logger.error(f"Invalid circle_id from ClawdChat: {circle_id}")
        return None


async def sync_event_post_update(
    post_id: str,
    event_title: str,
    event_description: Optional[str],
    event_slug: str,
    api_key: Optional[str] = None,
) -> bool:
    """Update the announce post when event content is edited. Returns True on success."""
    new_title, new_content = build_event_post_content(event_title, event_description, event_slug)
    result = await update_post(post_id, title=new_title, content=new_content, api_key=api_key)
    return result is not None
