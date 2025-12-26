import logging
from typing import Annotated, Optional

from fastapi import Cookie, Depends, HTTPException, status
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.security import NotAuthenticatedWebException
from ...core.db import get_db
from ...core.security import decode_access_token
from .crud import crud_user as crud
from .models import User, UserRole

# Setup logger
logger = logging.getLogger(__name__)


async def get_validated_user_or_none(
    db: AsyncSession, token: Optional[str],
) -> Optional[User]:
    """
    Returns User if the token is valid and the user is active, otherwise returns None.
    """
    if not token:
        return None

    try:
        payload = decode_access_token(token)
        google_sub: str = payload.get("sub")
        if not google_sub:
            return None

        user = await crud.get_user_by_google_sub(db, google_sub)
        if user and user.is_active:
            return user
    except Exception:
        pass

    return None


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Cookie(None, alias=settings.COOKIE_NAME),
) -> User:
    """
    Validates the user via HttpOnly Cookie.
    """
    user = await get_validated_user_or_none(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials.",
        )

    return user


async def get_current_user_web(
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Cookie(None, alias=settings.COOKIE_NAME),
) -> User:
    """
    Web-specific dependency. Raises NotAuthenticatedWebException on failure
    to trigger a redirect to the login page via exception handler.
    """
    if not token:
        raise NotAuthenticatedWebException()

    try:
        return await get_current_user(db, token)
    except HTTPException:
        raise NotAuthenticatedWebException()


async def get_csrf_token(csrf_protect: CsrfProtect = Depends()) -> str:
    """
    Generates and sets the CSRF token in the cookie.
    """
    return csrf_protect.generate_csrf_tokens()


# --- Type Definitions ---
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserWeb = Annotated[User, Depends(get_current_user_web)]
CsrfTokenWeb = Annotated[str, Depends(get_csrf_token)]


def require_role(required_roles: list[UserRole]):
    """
    Factory for role-based access control dependency.
    """
    def role_checker(current_user: CurrentUser) -> User:
        user_roles = {r.name.value for r in current_user.roles}
        req_roles = {r.value for r in required_roles}
        if not user_roles.intersection(req_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions.",
            )

        return current_user
    return role_checker
