from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from jose import jwt, JWTError # Thư viện cho JWT (JSON Web Token)

# Import models, schemas, và dependencies khác
from ..db import models, schemas
from ..db.base import get_db # Dependency lấy DB Session


# GIẢ ĐỊNH: Import cấu hình bảo mật
# Trong thực tế, các biến này sẽ được đọc từ app/core/config.py
class SecuritySettings:
    SECRET_KEY = "SECRET_KEY_CUC_KY_BAO_MAT_VA_CAN_DUOC_THAY_DOI" # Cần được thay đổi
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 ngày
    # Google Client ID/Secret sẽ được dùng để xác thực OAuth2 ban đầu (ngoài phạm vi file này)

security_settings = SecuritySettings()

# Khởi tạo context để băm mật khẩu
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Khởi tạo sơ đồ OAuth2 (sẽ dùng Bearer Token trong header Authorization)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/users/login/google")


# =======================================================================
# 1. Hashing Functions (Dành cho mật khẩu nếu có, hoặc mã hóa nội bộ)
# =======================================================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Kiểm tra mật khẩu thường và mật khẩu đã băm"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Băm mật khẩu"""
    return pwd_context.hash(password)


# =======================================================================
# 2. JWT Token Functions
# =======================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Tạo JWT Access Token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Thời gian hết hạn mặc định
        expire = datetime.utcnow() + timedelta(minutes=security_settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()}) # Thêm thời gian hết hạn và thời gian tạo
    encoded_jwt = jwt.encode(
        to_encode,
        security_settings.SECRET_KEY,
        algorithm=security_settings.ALGORITHM
    )

    return encoded_jwt

def get_user_by_token(db: Session, token: str) -> Optional[models.User]:
    """Giải mã Token và tìm kiếm User trong DB"""
    try:
        # 1. Giải mã token
        payload = jwt.decode(
            token,
            security_settings.SECRET_KEY,
            algorithms=[security_settings.ALGORITHM]
        )
        user_id: str = payload.get("sub") # Giả định subject là user_id
        if user_id is None:
            return None

        # 2. Tìm User trong DB
        user = db.get(models.User, uuid.UUID(user_id))
        if user is None:
            return None

        return user

    except JWTError:
        # Lỗi giải mã (token hết hạn, chữ ký sai, ...)
        return None
    except ValueError:
        # Lỗi UUID không hợp lệ
        return None


# =======================================================================
# 3. FastAPI Dependencies (Xác thực và Phân quyền RBAC)
# =======================================================================

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    """Dependency: Lấy người dùng hiện tại từ token"""
    user = get_user_by_token(db, token)
    if not user:
        # Token không hợp lệ hoặc User không tồn tại
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token không hợp lệ hoặc không tìm thấy người dùng",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """Dependency: Lấy người dùng hiện tại và kiểm tra trạng thái active"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Người dùng đã bị vô hiệu hóa"
        )

    return current_user


# -----------------------------------------------------------------------
# Các Dependencies Phân quyền RBAC (Role-Based Access Control)
# -----------------------------------------------------------------------

def is_admin(current_user: models.User = Depends(get_current_active_user)):
    """Dependency: Kiểm tra quyền ADMIN"""
    if current_user.role != schemas.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ ADMIN mới có quyền truy cập"
        )

    return current_user

def is_manager(current_user: models.User = Depends(get_current_active_user)):
    """Dependency: Kiểm tra quyền MANAGER hoặc ADMIN"""
    if current_user.role not in [schemas.UserRole.MANAGER, schemas.UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ MANAGER hoặc ADMIN mới có quyền truy cập"
        )

    return current_user

def is_checker(current_user: models.User = Depends(get_current_active_user)):
    """Dependency: Kiểm tra quyền CHECKER, MANAGER, hoặc ADMIN"""
    if current_user.role not in [schemas.UserRole.CHECKER, schemas.UserRole.MANAGER, schemas.UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Chỉ CHECKER, MANAGER hoặc ADMIN mới có quyền truy cập"
        )

    return current_user

# Các dependency này sẽ được sử dụng trực tiếp trong API Router:
# e.g. @router.post("/approve", dependencies=[Depends(is_checker)])
