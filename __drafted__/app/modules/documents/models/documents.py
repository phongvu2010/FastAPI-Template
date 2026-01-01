from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from .mixins import TimestampMixin

if TYPE_CHECKING:
    from .users import User


# --- Enums ---

class DocumentStatus(str, Enum):
    """
    Trạng thái của hồ sơ theo quy trình SignFlow.
    """
    DRAFT = "DRAFT"                           # Mới tạo, chưa gửi
    SUBMITTED = "SUBMITTED"                   # Đã gửi, chờ Checker
    LOCKED_BY_CHECKER = "LOCKED_BY_CHECKER"   # Checker đang xem, Sender không được sửa
    REJECTED = "REJECTED"                     # Bị trả về
    APPROVED = "APPROVED"                     # Checker đã duyệt (Ký nháy)
    COMPLETED = "COMPLETED"                   # Manager đã ký số pháp lý


class AuditAction(str, Enum):
    """
    Các hành động ghi nhận trong Audit Log.
    """
    CREATE = "CREATE"
    UPLOAD_VERSION = "UPLOAD_VERSION"
    SUBMIT = "SUBMIT"
    LOCK = "LOCK"
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    SIGN_INTERNAL = "SIGN_INTERNAL"
    SIGN_EXTERNAL = "SIGN_EXTERNAL"
    DELETE = "DELETE"  # Chỉ dùng cho Soft Delete hoặc Admin đặc biệt


# --- Models ---

class Document(TimestampMixin, SQLModel, table=True):
    """
    Bảng chứa thông tin chung (Metadata) của hồ sơ.
    Một hồ sơ có thể có nhiều phiên bản (DocumentVersion).
    """
    __tablename__ = "documents"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, index=True),
    )

    title: str = Field(index=True, max_length=255, nullable=False)
    description: Optional[str] = Field(default=None, sa_column=Column(Text))

    # Trạng thái hiện tại của quy trình
    status: DocumentStatus = Field(
        default=DocumentStatus.DRAFT,
        sa_column=Column(String, nullable=False, index=True) 
    )

    # Người tạo hồ sơ (thường là SENDER)
    creator_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True), 
            ForeignKey("users.id", ondelete="RESTRICT"), 
            nullable=False
        )
    )

    # Snapshot trỏ đến phiên bản mới nhất/được duyệt để query nhanh
    latest_version_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), nullable=True)
    )

    # Quan hệ
    creator: "User" = Relationship(back_populates="documents")
    versions: List["DocumentVersion"] = Relationship(
        back_populates="document", 
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    audit_logs: List["AuditLog"] = Relationship(back_populates="document")


class DocumentVersion(TimestampMixin, SQLModel, table=True):
    """
    Lưu trữ lịch sử các phiên bản file.
    Mỗi lần Upload lại (Re-upload) sẽ sinh ra một record mới ở đây.
    """
    __tablename__ = "document_versions"
    __table_args__ = (
        Index("ix_doc_version_unique", "document_id", "version_number", unique=True),
    )

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    document_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True), 
            ForeignKey("documents.id", ondelete="CASCADE"), 
            nullable=False
        )
    )

    version_number: int = Field(default=1, nullable=False)

    # Thông tin file vật lý
    file_path: str = Field(nullable=False, description="Đường dẫn lưu file (MinIO/Local)")
    file_name: str = Field(nullable=False, description="Tên file gốc lúc upload")
    file_size: int = Field(default=0)
    mime_type: str = Field(default="application/pdf")

    # QUAN TRỌNG: Mã băm để đảm bảo toàn vẹn dữ liệu (Data Integrity)
    file_hash: str = Field(
        nullable=False, 
        index=True, 
        description="SHA-256 Hash của file"
    )

    # Người upload phiên bản này
    uploaded_by_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    )

    # Quan hệ
    document: Document = Relationship(back_populates="versions")
    uploaded_by: "User" = Relationship()
    signatures: List["Signature"] = Relationship(back_populates="document_version")


class Signature(TimestampMixin, SQLModel, table=True):
    """
    Lưu trữ chữ ký số (Internal hoặc External).
    """
    __tablename__ = "signatures"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    document_version_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True), 
            ForeignKey("document_versions.id", ondelete="CASCADE"), 
            nullable=False
        )
    )

    signer_id: UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    )

    # Metadata chữ ký
    role: str = Field(description="Role của người ký tại thời điểm ký (CHECKER/MANAGER)")
    signature_type: str = Field(default="INTERNAL", description="INTERNAL (RSA) hoặc EXTERNAL (USB Token)")

    # Dữ liệu kỹ thuật
    signature_value: Optional[str] = Field(sa_column=Column(Text), description="Chuỗi ký tự chữ ký (Base64)")
    public_key: Optional[str] = Field(sa_column=Column(Text), description="Public Key dùng để verify")

    # Quan hệ
    document_version: DocumentVersion = Relationship(back_populates="signatures")
    signer: "User" = Relationship()


class AuditLog(SQLModel, table=True):
    """
    Nhật ký hệ thống (Audit Trail). Append-only.
    Không kế thừa TimestampMixin vì chỉ cần created_at (timestamp), không cần updated_at.
    """
    __tablename__ = "audit_logs"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )

    # Thời điểm xảy ra sự kiện
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)

    actor_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    )

    action: AuditAction = Field(sa_column=Column(String, nullable=False))

    # Context (Liên quan đến hồ sơ nào)
    document_id: Optional[UUID] = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL"))
    )

    # Chi tiết mở rộng (JSONB cho Postgres)
    details: Optional[dict] = Field(
        default={},
        sa_column=Column(JSONB)
    )

    # Quan hệ
    actor: Optional["User"] = Relationship()
    document: Optional[Document] = Relationship(back_populates="audit_logs")
