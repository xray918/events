"""OpenRouter LLM service for AI description generation."""

import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个专业的活动文案撰写助手。根据用户提供的活动基本信息，生成一份精美的 Markdown 格式活动描述。

要求：
1. 使用 Markdown 格式，包含标题、分段、列表、加粗等
2. 风格专业、有吸引力，简洁有力
3. 包含以下部分（根据信息灵活调整）：
   - 一段引人入胜的开场介绍
   - 活动亮点（用列表）
   - 适合参加的人群
   - 活动议程概览（如有足够信息）
   - 温馨提示
4. 不要编造具体嘉宾、具体议程时间等未提供的信息
5. 如果用户已提供描述文本，在其基础上润色和结构化，保留原始信息
6. 整体长度适中，不超过 500 字
7. 不要在最外层加标题（活动名称已在页面显示）"""


async def generate_event_description(
    title: str,
    event_type: str = "in_person",
    location: Optional[str] = None,
    start_time: Optional[str] = None,
    existing_description: Optional[str] = None,
) -> Optional[str]:
    """Call OpenRouter LLM to generate a Markdown event description."""
    if not settings.openrouter_api_key:
        logger.warning("OpenRouter API key not configured")
        return None

    user_msg_parts = [f"活动名称：{title}", f"活动类型：{event_type}"]
    if location:
        user_msg_parts.append(f"地点：{location}")
    if start_time:
        user_msg_parts.append(f"时间：{start_time}")
    if existing_description:
        user_msg_parts.append(f"\n已有描述（请在此基础上润色）：\n{existing_description}")
    else:
        user_msg_parts.append("\n请根据以上信息生成活动描述。")

    user_msg = "\n".join(user_msg_parts)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{settings.openrouter_api_base}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.openrouter_model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_msg},
                    ],
                    "max_tokens": 1500,
                    "temperature": 0.7,
                },
            )

        if resp.status_code != 200:
            logger.error(f"OpenRouter API error: {resp.status_code} {resp.text[:300]}")
            return None

        data = resp.json()
        content = data.get("choices", [{}])[0].get("message", {}).get("content")
        return content

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        return None
