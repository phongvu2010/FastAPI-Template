import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any


# =======================================================================
# 1. Enums (Dựa trên Choices của Django)
# =======================================================================

class UserRole(str, Enum):
    """Vai trò người dùng dựa trên blueprint"""
    SENDER = "SENDER"
    CHECKER = "CHECKER"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"

class DocumentStatus(str, Enum):
    """Trạng thái tài liệu dựa trên blueprint"""
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    APPROVED_FOR_SIGNING = "APPROVED_FOR_SIGNING"
    COMPLETED_INTERNAL = "COMPLETED_INTERNAL"
    COMPLETED_EXTERNAL = "COMPLETED_EXTERNAL"

class SignatureType(str, Enum):
    """Loại chữ ký"""
    INTERNAL = "INTERNAL"
    EXTERNAL = "EXTERNAL"


# =======================================================================
# 2. User Schemas
# =======================================================================

# Schema cơ bản, dùng chung
class UserBase(BaseModel):
    """Schema cơ bản cho User, chỉ chứa email"""
    email: EmailStr
    # Bạn có thể thêm first_name, last_name nếu cần

# Schema dùng khi tạo User (ví dụ: admin tạo hoặc tự đăng ký)
class UserCreate(UserBase):
    """Schema khi tạo User.

    Lưu ý: Mật khẩu được quản lý bởi Google SSO / fastapi-users,
    không lưu ở đây.
    """
    role: UserRole = UserRole.SENDER # Mặc định
    # Lưu ý: 'fastapi-users' sẽ xử lý mật khẩu riêng

# Schema dùng khi đọc thông tin User (trả về từ API)
class UserRead(UserBase):
    """Schema trả về khi đọc thông tin User"""
    id: uuid.UUID  # Giả định User model dùng UUID giống Document
    role: UserRole
    is_active: bool = True # Giả định từ fastapi-users

    class Config:
        # Cho phép Pydantic đọc từ SQLAlchemy model
        from_attributes = True # Dùng cho Pydantic v2 (hoặc orm_mode = True cho v1)


# =======================================================================
# 3. Document & DocumentVersion Schemas
# =======================================================================

# --- DocumentVersion ---
# Định nghĩa DocumentVersion trước để DocumentRead có thể tham chiếu

# Schema cơ bản cho DocumentVersion
class DocumentVersionBase(BaseModel):
    """Schema cơ sở cho DocumentVersion"""
    notes: Optional[str] = None

# Schema khi đọc một DocumentVersion (trả về từ API)
class DocumentVersionRead(DocumentVersionBase):
    """Schema trả về khi đọc DocumentVersion"""
    id: uuid.UUID
    document_id: uuid.UUID
    uploaded_by_id: uuid.UUID # Chúng ta sẽ dùng ID thay vì lồng object User
    uploaded_at: datetime
    file_hash: str = Field(..., max_length=128) # SHA-256
    version_number: int
    file_path: str

    class Config:
        # Cho phép Pydantic đọc từ SQLAlchemy model
        from_attributes = True # Dùng cho Pydantic v2 (hoặc orm_mode = True cho v1)


# --- Document ---

# Schema cơ bản cho Document
class DocumentBase(BaseModel):
    """Schema cơ sở cho Document"""
    title: str = Field(..., max_length=512)
    metadata: Optional[Dict[str, Any]] = {}

# Schema dùng khi tạo Document (từ endpoint upload)
class DocumentCreate(DocumentBase):
    """Schema khi tạo Document (dùng cho endpoint upload)"""
    # creator_id sẽ được lấy từ user đã đăng nhập,
    # không cần client gửi lên
    pass # title và metadata là đủ, file được xử lý riêng

# Schema dùng để đọc thông tin Document (trả về từ API)
class DocumentRead(DocumentBase):
    """Schema trả về khi đọc danh sách Document"""
    id: uuid.UUID
    creator_id: uuid.UUID
    created_at: datetime
    status: DocumentStatus

    # ID của phiên bản đã được duyệt
    approved_version_id: Optional[uuid.UUID] = None

    class Config:
        # Cho phép Pydantic đọc từ SQLAlchemy model
        from_attributes = True # Dùng cho Pydantic v2 (hoặc orm_mode = True cho v1)

# Schema đầy đủ khi xem chi tiết Document,
# bao gồm các phiên bản của nó
class DocumentReadDetail(DocumentRead):
    """Schema trả về khi xem chi tiết, bao gồm các phiên bản"""
    versions: List[DocumentVersionRead] = []
    creator: Optional[UserRead] = None # Lồng thông tin người tạo


# =======================================================================
# 4. Signature & AuditLog Schemas
# =======================================================================

# --- Signature ---

class SignatureBase(BaseModel):
    """Schema cơ sở cho Signature"""
    sig_type: SignatureType
    meta: Optional[Dict[str, Any]] = {}

class SignatureCreate(SignatureBase):
    """Schema khi tạo chữ ký (dùng nội bộ trong service)"""
    signature_blob: bytes
    public_key: str

class SignatureRead(SignatureBase):
    """Schema trả về khi đọc Signature"""
    id: uuid.UUID
    document_version_id: uuid.UUID
    signer_id: Optional[uuid.UUID] = None
    public_key: str
    created_at: datetime

    class Config:
        # Cho phép Pydantic đọc từ SQLAlchemy model
        from_attributes = True # Dùng cho Pydantic v2 (hoặc orm_mode = True cho v1)

# --- AuditLog ---

class AuditLogBase(BaseModel):
    """Schema cơ sở cho AuditLog"""
    action: str = Field(..., max_length=100)
    details: Optional[Dict[str, Any]] = {}

class AuditLogCreate(AuditLogBase):
    """Schema dùng nội bộ để tạo AuditLog (thông qua helper)"""
    actor_id: Optional[uuid.UUID] = None
    document_id: Optional[uuid.UUID] = None
    document_version_id: Optional[uuid.UUID] = None

class AuditLogRead(AuditLogBase):
    """Schema trả về khi đọc AuditLog"""
    id: int # BigAutoField
    timestamp: datetime
    actor_id: Optional[uuid.UUID]
    document_id: Optional[uuid.UUID]
    document_version_id: Optional[uuid.UUID]

    actor: Optional[UserRead] = None # Lồng thông tin actor để dễ hiển thị

    class Config:
        # Cho phép Pydantic đọc từ SQLAlchemy model
        from_attributes = True # Dùng cho Pydantic v2 (hoặc orm_mode = True cho v1)
