import asyncio
import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode

import httpx
from fastapi import HTTPException, status
from google.auth.transport import requests
from google.oauth2 import id_token
from jose import JWTError, jwt

from .config import settings

logger = logging.getLogger(__name__)

# Google OAuth Constant URLs
GOOGLE_OAUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


# --- Google OAuth & CSRF Utilities ---

def generate_state_token() -> str:
    """
    Generates a secure, random string for CSRF protection.
    """
    return secrets.token_urlsafe(32)


def create_google_auth_url(state: str) -> str:
    """
    Constructs the Google OAuth authorization URL.
    """
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "select_account",
        "state": state,
    }
    return f"{GOOGLE_OAUTH_URL}?{urlencode(params)}"


async def exchange_code_for_token(code: str) -> dict[str, Any]:
    """
    Exchanges Google authorization code for an ID Token.
    """
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    # Use httpx.AsyncClient for asynchronous network request
    async with httpx.AsyncClient() as client:
        response = await client.post(GOOGLE_TOKEN_URL, data=data)
        response.raise_for_status()
        return response.json()


async def get_google_user_info_async(id_token_str: str) -> dict[str, Any]:
    """
    Asynchronously verifies Google ID Token and extracts user info.
    Runs the blocking Google library call in a separate thread.
    """
    loop = asyncio.get_running_loop()
    try:
        user_info = await loop.run_in_executor(
            None,
            lambda: id_token.verify_oauth2_token(
                id_token_str,
                requests.Request(),
                settings.GOOGLE_CLIENT_ID,
            ),
        )
        return user_info
    except ValueError as e:
        logger.warning(f"Google ID Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google ID token.",
        )


# --- Internal JWT Utilities ---

def create_access_token(user_id: str) -> str:
    """
    Creates an internal JWT access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode = {"exp": expire, "sub": user_id}
    return jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decodes and validates the internal JWT Token.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        )
