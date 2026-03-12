"""Google OAuth 2.0 service (adapted from ClawdChat)."""

import logging
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL = "https://oauth2.googleapis.com/token"
    USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri

    def get_auth_url(self, state: str = "login") -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": "email profile",
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }
        return f"{self.AUTH_URL}?{urlencode(params)}"

    async def exchange_code(self, code: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if resp.status_code != 200:
                logger.error(f"Google token exchange failed: {resp.text}")
                return None
            return resp.json()

    async def get_user_info(self, access_token: str) -> Optional[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code != 200:
                logger.error(f"Google userinfo failed: {resp.text}")
                return None
            return resp.json()

    async def authenticate(self, code: str) -> Optional[dict]:
        token_data = await self.exchange_code(code)
        if not token_data:
            return None
        access_token = token_data.get("access_token")
        if not access_token:
            logger.error("No access_token in Google response")
            return None
        return await self.get_user_info(access_token)


google_service = GoogleOAuthService()
