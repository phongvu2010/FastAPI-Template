from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from api.deps import CurrentUser, require_role
from db.models import UserRole, User
from db.schemas import UserRead, UserUpdateStatus, UserUpdateRole
from services import user_service
from db.base import get_db


# @router.patch("/{user_id}/status", response_model=UserRead)
# async def update_status(
#     user_id: int,
#     status_in: UserUpdateStatus,
#     db: AsyncSession = Depends(get_db),
#     current_user: User = Depends(require_role([UserRole.ADMIN])),
# ):
#     """Cập nhật trạng thái Active/Inactive (Admin only)."""
#     if user_id == current_user.id and not status_in.is_active:
#         raise HTTPException(
#             status_code=400, detail="Không thể tự khóa tài khoản chính mình."
#         )

#     user = await user_crud.get_user_by_id(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found.")

#     return await user_crud.update_user_status(db, user, status_in.is_active)


@router.patch("/{user_id}/status", response_model=UserRead)
async def update_status(
    user_id: int,
    status_in: UserUpdateStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN])),
):
    """
    HTMX: Cập nhật trạng thái Active/Inactive.
    Trả về: Partial HTML (<tr>...</tr>) của dòng user đã cập nhật.
    """
    # 1. Chặn Admin tự khóa chính mình
    if user_id == current_user.id and not status_in.is_active:
        # Trả về dòng cũ kèm script thông báo
        all_roles = await user_service.get_all_roles(db)
        
        # Render row cũ
        row_html = templates.TemplateResponse(
            "partial/user_row.html",
            {"request": request, "u": current_user, "roles": all_roles}
        ).body
        
        # Đính kèm script alert
        return HTMLResponse(
            content=row_html + b'<script>alert("ERORR: Ban khong the tu khoa tai khoan cua chinh minh!");</script>'
        )

    user = await user_service.get_user_by_id(db, user_id)
    if user:
        user = await user_service.update_user_status(db, user, is_active)

    # Lấy danh sách roles để render lại dropdown
    all_roles = await user_service.get_all_roles(db)

    return templates.TemplateResponse(
        "partial/user_row.html",
        {
            "request": request,
            "u": user,
            "roles": all_roles,
        },
    )


# @router.post("/{user_id}/roles", response_model=UserRead)
# async def assign_role(
#     user_id: int,
#     role_in: UserUpdateRole,
#     db: AsyncSession = Depends(get_db),
#     _: User = Depends(require_role([UserRole.ADMIN])),
# ):
#     """Gán Role cho user (Admin only)."""
#     user = await user_crud.get_user_by_id(db, user_id)
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found.")

#     try:
#         return await user_crud.assign_role_to_user(db, user, role_in.role_name)
#     except ValueError as e:
#         raise HTTPException(status_code=400, detail=str(e))
