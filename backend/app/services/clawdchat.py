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


async def publish_event_to_clawdchat(
    event_title: str,
    event_description: Optional[str],
    event_slug: str,
    agent_api_key: Optional[str] = None,
) -> Optional[UUID]:
    """Create a Circle + announce post for a published event.

    - If agent_api_key is provided (agent publishes), use that agent's key.
    - Otherwise (human publishes), use EventsBot's key.

    Returns the created circle UUID or None if creation failed.
    """
    api_key = agent_api_key or settings.events_bot_api_key

    circle_name = f"🎉 {event_title}"
    circle_desc = (event_description or "")[:500]
    if circle_desc:
        circle_desc = f"活动圈子 — {circle_desc}"
    else:
        circle_desc = f"活动圈子 — {event_title}"

    circle = await create_circle(circle_name, circle_desc, api_key=api_key)
    if not circle:
        return None

    circle_id = circle.get("id")

    event_url = f"{settings.frontend_url}/e/{event_slug}"
    post_content = (
        f"📢 **{event_title}** 活动已发布！\n\n"
        f"{event_description or ''}\n\n"
        f"👉 报名链接：{event_url}\n\n"
        f"欢迎参加，期待与你相见！"
    )

    await create_post(
        circle_name=circle_name,
        title=f"📢 活动发布：{event_title}",
        content=post_content,
        url=event_url,
        api_key=api_key,
    )

    try:
        return UUID(str(circle_id))
    except (ValueError, TypeError):
        logger.error(f"Invalid circle_id from ClawdChat: {circle_id}")
        return None
