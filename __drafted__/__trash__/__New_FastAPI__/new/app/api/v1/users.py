import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from ...db.base import get_db
from ...db import models, schemas
from ...core.security import create_access_token
from ...core.config import settings
from datetime import timedelta


router = APIRouter(
    prefix="/users",
    tags=["Users & Authentication"]
)

# --- PLACEHOLDER SCHEMA TRẢ VỀ CHO AUTH ---
class Token(schemas.BaseModel):
    access_token: str
    token_type: str = "bearer"

# =======================================================================
# ENDPOINT AUTH (GIẢ LẬP GOOGLE SSO)
# =======================================================================

@router.post(
    "/login/google",
    response_model=Token,
    summary="Giả lập Google SSO: Lấy JWT Token"
)
async def google_sso_login_mock(
    # Trong thực tế, bạn sẽ nhận 'code' từ Google và trao đổi để lấy thông tin User
    email: str = "checker@secure.com", # Giả định email của người dùng
    db: Session = Depends(get_db)
):
    """
    Giả lập việc xác thực qua Google và tạo Access Token.
    Trong thực tế, hàm này sẽ gọi Google API để lấy user info.
    """

    # 1. Tìm hoặc tạo User trong DB dựa trên email
    # Giả định User đã tồn tại (ví dụ: CHECKER)
    user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        # Nếu không tìm thấy, tạo User mới (ví dụ: SENDER)
        user = models.User(
            email=email,
            role=schemas.UserRole.SENDER,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # 2. Tạo JWT Access Token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value}, # Lưu ID và Role vào Token
        expires_delta=access_token_expires
    )

    return {"access_token": access_token}

@router.get(
    "/me",
    response_model=schemas.UserRead,
    summary="Lấy thông tin người dùng hiện tại"
)
async def read_users_me(
    current_user: models.User = Depends(get_current_active_user)
):
    """Trả về thông tin của người dùng hiện đang được xác thực."""
    return current_user
