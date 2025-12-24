from typing import Optional

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.deps import CsrfTokenWeb, CurrentUserWeb, get_validated_user_or_none
from ..core.config import settings
from ..core.db import get_db
from ..modules.auth.crud import crud_user as crud
from ..modules.auth.models import UserRole, User
from ..modules.auth.models.users import DEPARTMENTS

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="templates")


def render_error_response(
    request: Request,
    title: str,
    detail: str,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    user: Optional[User] = None,
) -> Response:
    """
    Helper to render error page.
    """
    return templates.TemplateResponse(
        "error_page.html",
        {
            "request": request,
            "error_message": title,
            "detail": detail,
            "user": user,
        },
        status_code=status_code,
    )


@router.get("/", response_class=HTMLResponse, name="dashboard_page")
async def dashboard_page(
    request: Request,
    current_user: CurrentUserWeb,
    csrf_token: CsrfTokenWeb,
):
    """
    Renders the dashboard.
    """
    user_role_names = {r.name for r in current_user.roles}

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "roles": user_role_names,
            "is_admin": UserRole.ADMIN in user_role_names,
            "csrf_token": csrf_token,
        },
    )


@router.get("/login", response_class=HTMLResponse, name="login_page")
async def login_page(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Renders login page.
    """
    # Get cookie token
    token = request.cookies.get(settings.COOKIE_NAME)

    if token:
        user = await get_validated_user_or_none(db, token)
        if user:
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)

    response = templates.TemplateResponse(
        "auth/login.html",
        {
            "request": request,
            "login_url": request.url_for("google_login"),
        },
    )

    if token:
        response.delete_cookie(settings.COOKIE_NAME)

    return response


@router.get("/admin", response_class=HTMLResponse)
async def admin_panel(
    request: Request,
    csrf_token: CsrfTokenWeb,
    current_user: CurrentUserWeb,
    db: AsyncSession = Depends(get_db),
):
    """
    Renders admin panel (Admin only).
    """
    user_role_names = {r.name for r in current_user.roles}

    # Manual Role Check
    if UserRole.ADMIN not in user_role_names:
        return render_error_response(
            request=request,
            title="Access Forbidden",
            detail="Admin privileges required.",
            status_code=status.HTTP_403_FORBIDDEN,
            user=current_user,
        )

    # Fetch data
    users = await crud.get_all_users(db)
    roles = await crud.get_all_roles(db)

    return templates.TemplateResponse(
        "admin/admin_panel.html",
        {
            "request": request,
            "user": current_user,
            "users": users,
            "roles": roles,
            "csrf_token": csrf_token,
            "api_user_prefix": "/api/v1/users",
            "is_admin": True  # Use the flag utility to highlight the menu
        },
    )


@router.get("/profile", response_class=HTMLResponse, name="profile_page")
async def profile_page(
    request: Request,
    current_user: CurrentUserWeb,
    csrf_token: CsrfTokenWeb,
):
    """
    Renders profile page.
    """
    return templates.TemplateResponse(
        "profile.html",
        {
            "request": request,
            "user": current_user,
            "csrf_token": csrf_token,
            "departments": DEPARTMENTS,
        },
    )


@router.get("/error", response_class=HTMLResponse)
async def error_page(
    request: Request,
    title: str = "An Error Occurred",
    detail: Optional[str] = "The requested resource could not be loaded.",
    status_code: int = status.HTTP_200_OK,
):
    """
    Generic error page.
    """
    return render_error_response(
        request,
        title,
        detail,
        status_code,
    )
