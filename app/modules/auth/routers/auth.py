import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core import security
from ....core.config import settings
from ....core.db import get_db
from ..services.auth_service import AuthService
from ....web.views import render_error_response

router = APIRouter(tags=["auth"])
logger = logging.getLogger(__name__)


@router.get("/login/redirect")
async def google_login(response: Response):
    """
    Initiates Google OAuth flow with CSRF state.
    """
    # 1. Create CSRF state
    state = security.generate_state_token()
    auth_url = security.create_google_auth_url(state)

    resp = RedirectResponse(url=auth_url, status_code=status.HTTP_302_FOUND)

    # 2. Store state in a short-lived, HttpOnly cookie for verification
    resp.set_cookie(
        key="oauth_state",
        value=state,
        max_age=300,  # 5 minutes
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return resp


@router.get("/logout")
async def logout(request: Request):
    """
    Logs out by clearing the session cookie.
    """
    resp = RedirectResponse(
        url=request.url_for("login_page"),
        status_code=status.HTTP_302_FOUND,
    )

    # Ensure all parameters match the set_cookie call for reliable deletion
    resp.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.COOKIE_SECURE,
    )
    return resp


@router.get("/callback")
async def google_callback(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    code: Optional[str] = None,
    state: Optional[str] = None,
    state_in_cookie: Optional[str] = Cookie(None, alias="oauth_state"),
):
    """
    Handles Google OAuth callback.
    """
    if not code or not state:
        return render_error_response(
            request,
            title="Authentication Error",
            detail="Missing parameters from Google.",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = await AuthService.authenticate_google_user(
            db, code, state, state_in_cookie
        )

        access_token = security.create_access_token(user.google_sub)

        response = RedirectResponse(
            url=request.url_for("dashboard_page"),
            status_code=status.HTTP_302_FOUND,
        )

        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=access_token,
            max_age=settings.COOKIE_MAX_AGE,
            httponly=True,
            samesite="lax",
            secure=settings.COOKIE_SECURE,
        )

        response.delete_cookie(
            key="oauth_state",
            path="/",
            samesite="lax",
            secure=settings.COOKIE_SECURE,
        )

        return response

    except HTTPException as http_exc:
        logger.warning(f"Auth Error: {http_exc.detail}")
        return render_error_response(
            request,
            title="Authentication Failed",
            detail=str(http_exc.detail),
            status_code=http_exc.status_code,
        )

    except Exception:
        logger.error("System error during auth callback", exc_info=True)
        return render_error_response(
            request,
            title="System Error",
            detail="Unexpected error occurred.",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
