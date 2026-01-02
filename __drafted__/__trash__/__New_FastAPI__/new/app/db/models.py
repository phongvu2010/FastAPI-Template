import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

# SQLAlchemy imports
from sqlalchemy import (
    Column, String, ForeignKey, Integer, DateTime, func, Enum, Text, LargeBinary,
    UniqueConstraint, Index, BigInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB # Dùng UUID và JSONB cho Postgres
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Lấy Base từ file base.py (giả định)
# from .base import Base
Base = declarative_base() # Tạm thời dùng Base mặc định

# Import Enums từ schemas để đồng bộ
from ..db.schemas import UserRole, DocumentStatus, SignatureType


# =======================================================================
# 1. User Model
# =======================================================================

class User(Base):
    """
    Kế thừa từ AbstractUser (Blueprint) - Tùy chỉnh cho Google SSO.
    """
    __tablename__ = "user"

    # Giả định User ID dùng UUID để đồng bộ với các model khác
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)

    # Role (SENDER, CHECKER, MANAGER, ADMIN)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name='user_role_enum'), default=UserRole.SENDER
    )
    is_active: Mapped[bool] = mapped_column(default=True)

    # Quan hệ ngược (Reverse relationships)
    created_documents: Mapped[List["Document"]] = relationship(
        back_populates="creator"
    )
    uploaded_versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="uploaded_by"
    )
    signed_signatures: Mapped[List["Signature"]] = relationship(
        back_populates="signer"
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        back_populates="actor"
    )


# =======================================================================
# 2. Document Model
# =======================================================================

class Document(Base):
    """
    Hồ sơ gốc - Quản lý metadata và trạng thái.
    """
    __tablename__ = "document"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name='document_status_enum'),
        default=DocumentStatus.PENDING,
        index=True # Index theo Blueprint
    )
    metadata: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default='{}'
    )

    # Quan hệ 1-n User (creator)
    creator_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="PROTECT") # Theo Blueprint
    )
    creator: Mapped["User"] = relationship(
        back_populates="created_documents"
    )

    # Quan hệ 1-1 DocumentVersion (approved_version) - Ký nháy
    # Sử dụng None cho `remote_side` và `primaryjoin` cho quan hệ 1-1 tự tham chiếu
    approved_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("document_version.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Dùng relationship riêng cho approved_version (tương tự related_name="+")
    approved_version: Mapped[Optional["DocumentVersion"]] = relationship(
        primaryjoin="Document.approved_version_id == DocumentVersion.id",
        remote_side="DocumentVersion.id",
        uselist=False
    )

    # Quan hệ 1-n DocumentVersion
    versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="document",
        order_by="DocumentVersion.version_number.desc()"
    )


# =======================================================================
# 3. DocumentVersion Model
# =======================================================================

class DocumentVersion(Base):
    """
    Phiên bản hồ sơ cụ thể, lưu trữ file và hash.
    """
    __tablename__ = "document_version"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    # Đường dẫn file (tương đương FileField)
    file_path: Mapped[str] = mapped_column(String(512))
    file_hash: Mapped[str] = mapped_column(
        String(128), index=True # SHA-256
    )
    version_number: Mapped[int] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Foreign Keys
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document.id", ondelete="CASCADE") # CASCADE
    )
    document: Mapped["Document"] = relationship(
        back_populates="versions"
    )

    uploaded_by_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user.id", ondelete="PROTECT")
    )
    uploaded_by: Mapped["User"] = relationship(
        back_populates="uploaded_versions"
    )

    # Quan hệ 1-n Signature
    signatures: Mapped[List["Signature"]] = relationship(
        back_populates="document_version"
    )

    # Constraints
    __table_args__ = (
        # unique_together = ("document", "version_number")
        UniqueConstraint("document_id", "version_number", name="uq_document_version"),
        # ordering = ["-version_number"] - Đã xử lý trong Document.versions
    )


# =======================================================================
# 4. Signature Model
# =======================================================================

class Signature(Base):
    """
    Lưu trữ chữ ký nội bộ hoặc metadata của chữ ký bên ngoài.
    """
    __tablename__ = "signature"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )

    sig_type: Mapped[SignatureType] = mapped_column(
        Enum(SignatureType, name='signature_type_enum')
    )

    # Lưu trữ bytes (e.g. signed hash)
    signature_blob: Mapped[bytes] = mapped_column(LargeBinary)
    # Lưu trữ public key pem
    public_key: Mapped[str] = mapped_column(Text)

    meta: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default='{}'
    )

    # Foreign Keys
    document_version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_version.id", ondelete="CASCADE")
    )
    document_version: Mapped["DocumentVersion"] = relationship(
        back_populates="signatures"
    )

    # null if external
    signer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    signer: Mapped[Optional["User"]] = relationship(
        back_populates="signed_signatures"
    )


# =======================================================================
# 5. AuditLog Model
# =======================================================================

class AuditLog(Base):
    """
    Ghi nhật ký hành động không thể xóa/sửa (Immutable Log).
    """
    __tablename__ = "audit_log"

    # BigAutoField trong Django tương đương BigInteger trong SQLAlchemy
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        index=True # db_index=True
    )
    action: Mapped[str] = mapped_column(String(100)) # e.g. UPLOAD, APPROVE
    details: Mapped[Dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default='{}'
    )

    # Foreign Keys (Tất cả đều nullable=True vì không phải hành động nào cũng liên quan đến tất cả)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    actor: Mapped[Optional["User"]] = relationship(
        back_populates="audit_logs"
    )

    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("document.id", ondelete="SET NULL"), nullable=True
    )
    document: Mapped[Optional["Document"]] = relationship()

    document_version_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("document_version.id", ondelete="SET NULL"), nullable=True
    )
    document_version: Mapped[Optional["DocumentVersion"]] = relationship()

    __table_args__ = (
        # ordering = ["-timestamp"] - Dùng trong truy vấn thay vì định nghĩa ở đây
        # Sẽ áp dụng trigger Postgres để ngăn xóa
    )
