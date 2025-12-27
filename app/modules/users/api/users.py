from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_csrf_protect import CsrfProtect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from .. import crud as crud
from ..dependencies import CurrentUser, require_role
from ..models import (
    User,
    UserRead,
    UserRole,
    UserUpdateProfile,
    UserUpdateRole,
    UserUpdateStatus,
)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_current_user(current_user: CurrentUser):
    """
    Retrieves the current authenticated user.
    """
    return current_user


@router.get("/", response_model=List[UserRead])
async def read_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    Retrieves all users (Admin only).
    """
    return await crud.get_all_users(db)


@router.patch("/me", response_model=UserRead)
async def update_my_profile(
    profile_in: UserUpdateProfile,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    csrf_protect: CsrfProtect = Depends(),
):
    """
    Updates current user profile.
    """
    update_data = profile_in.model_dump(exclude_unset=True)

    try:
        return await crud.update_user_profile(db, current_user, update_data)
    except IntegrityError as e:
        if "contact_email" in str(e.orig):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This contact email address is already being used by another account.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The data is invalid or duplicated."
        )


@router.patch("/{user_id}/status", response_model=UserRead)
async def update_status(
    user_id: UUID,
    status_in: UserUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    csrf_protect: CsrfProtect = Depends(),
):
    """
    Updates user status (Admin only).
    """
    if user_id == current_user.id and not status_in.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account.",
        )

    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return await crud.update_user_status(db, user, status_in.is_active)


@router.post("/{user_id}/role", response_model=UserRead)
async def add_role(
    user_id: UUID,
    role_in: UserUpdateRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    csrf_protect: CsrfProtect = Depends(),
):
    """
    Adds a role to a user (Admin only).
    """
    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    role = await crud.get_role_by_name(db, role_in.role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    try:
        return await crud.add_role_to_user(db, user, role)
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete("/{user_id}/role", response_model=UserRead)
async def remove_role(
    user_id: UUID,
    role_in: UserUpdateRole,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
    csrf_protect: CsrfProtect = Depends(),
):
    """
    Removes a role from a user (Admin only).
    """
    if user_id == current_user.id and role_in.role_name == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove Admin role from yourself.",
        )

    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    role = await crud.get_role_by_name(db, role_in.role_name)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found.",
        )

    return await crud.remove_role_from_user(db, user, role)
