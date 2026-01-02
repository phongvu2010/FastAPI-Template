from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ...db.base import get_db
from ...db import models, schemas
from ...core.security import is_admin # Dependency kiểm tra quyền ADMIN

router = APIRouter(
    prefix="/admin",
    tags=["Admin Management"]
)

@router.get(
    "/users",
    response_model=List[schemas.UserRead],
    dependencies=[Depends(is_admin)], # Chỉ ADMIN mới được truy cập
    summary="[ADMIN] Lấy danh sách tất cả người dùng"
)
def read_all_users(
    db: Session = Depends(get_db),
    # Dùng is_admin ở đây để xác nhận quyền và lấy đối tượng user nếu cần
    admin_user: models.User = Depends(is_admin)
):
    """
    Truy xuất danh sách tất cả người dùng trong hệ thống (chỉ dành cho ADMIN).
    """
    users = db.query(models.User).all()
    return users

@router.get(
    "/audit-logs",
    response_model=List[schemas.AuditLogRead],
    dependencies=[Depends(is_admin)], # Chỉ ADMIN mới được truy cập
    summary="[ADMIN] Xem toàn bộ Audit Log"
)
def read_all_audit_logs(
    db: Session = Depends(get_db),
):
    """
    Truy xuất toàn bộ lịch sử Audit Log (chỉ dành cho ADMIN).
    """
    # Lấy 100 log gần nhất
    logs = db.query(models.AuditLog).order_by(models.AuditLog.timestamp.desc()).limit(100).all()
    return logs
