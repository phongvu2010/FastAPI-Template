import logging
import os

from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ....core.config import settings
from ....db.database import get_db
from .. import crud
from ..dependencies import CsrfTokenWeb, CurrentUserWeb, get_validated_user_or_none
from ..models import UserRole, User
from ..models.user import DEPARTMENTS

router = APIRouter(tags=["frontend"])
logger = logging.getLogger(__name__)

# Configure the module to automatically find its own template.
module_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
templates = Jinja2Templates(directory=[
    module_dir,             # Ưu tiên template trong module
    "app/templates",        # Dự phòng template chung (base.html)
])


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
        # raise HTTPException(
        #     status_code=status.HTTP_403_FORBIDDEN,
        #     detail="Admin privileges required.",
        # )
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
            "is_admin": True,  # Use the flag utility to highlight the menu
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
    user_role_names = {r.name for r in current_user.roles}
    return templates.TemplateResponse(
        "auth/profile.html",
        {
            "request": request,
            "user": current_user,
            "csrf_token": csrf_token,
            "departments": DEPARTMENTS,
            "is_admin": UserRole.ADMIN in user_role_names,
        },
    )
