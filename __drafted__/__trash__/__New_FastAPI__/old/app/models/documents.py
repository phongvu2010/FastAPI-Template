from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from models.__init__ import Base

# --- Bảng DOCUMENT_VERSIONS (Phiên bản File) ---
class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)

    # Đường dẫn file trên local server (tương đối)
    relative_path = Column(Text, nullable=False)

    # Hash file để kiểm tra tính toàn vẹn
    file_hash = Column(String(64), nullable=False) # SHA-256 hash

    # Chi tiết phiên bản
    action_description = Column(Text)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())

    # Đánh dấu ký nháy
    is_signed_internally = Column(Boolean, default=False)

    # Định nghĩa quan hệ
    document = relationship("Document", back_populates="versions", foreign_keys=[document_id])
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    # Đảm bảo mỗi hồ sơ không có 2 số version giống nhau
    __table_args__ = (
        UniqueConstraint("document_id", "version_number", name="_document_version_uc"),
    )

# --- Bảng DOCUMENTS (Hồ sơ) ---
class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    document_code = Column(String(50), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)

    # Khóa ngoại liên kết người dùng
    uploader_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    inspector_id = Column(Integer, ForeignKey("users.id")) # Người duyệt (có thể null lúc đầu)
    signer_id = Column(Integer, ForeignKey("users.id")) # Người ký (có thể null lúc đầu)

    # Trạng thái hiện tại
    # Các trạng thái tiềm năng: SUBMITTED, REJECTED_BY_INSPECTOR, INTERNALLY_SIGNED,
    # VALIDATING (sau khi sếp upload), COMPLETED_EXTERNAL, COMPLETED_INTERNAL, VALIDATION_FAILED
    status = Column(String(50), nullable=False, default="SUBMITTED")

    # Liên kết Phiên bản
    current_version_id = Column(Integer, ForeignKey("document_versions.id", use_alter=True, ondelete="SET NULL")) # Phiên bản file mới nhất đang được xử lý

    # Thời gian
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Định nghĩa quan hệ
    uploader = relationship("User", foreign_keys=[uploader_id], back_populates="uploaded_documents")
    inspector = relationship("User", foreign_keys=[inspector_id], back_populates="inspected_documents")
    signer = relationship("User", foreign_keys=[signer_id], back_populates="signed_documents")
    versions = relationship("DocumentVersion", back_populates="document", foreign_keys=[DocumentVersion.document_id])
    logs = relationship("AuditLog", back_populates="document")

    # Quan hệ tự tham chiếu (Self-referencing relationship) cho current_version_id
    current_version = relationship("DocumentVersion", foreign_keys=[current_version_id], post_update=True)

# --- Bảng AUDIT_LOGS (Nhật ký Kiểm toán) ---
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Loại hành động (SUBMIT, REJECT, INTERNAL_SIGN, EXTERNAL_UPLOAD...)
    action = Column(String(50), nullable=False)

    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(Text) # Lý do từ chối, Ghi chú hành động

    # Liên kết với phiên bản file liên quan
    related_version_id = Column(Integer, ForeignKey("document_versions.id", ondelete="SET NULL"))

    # Định nghĩa quan hệ
    document = relationship("Document", back_populates="logs")
    user = relationship("User", back_populates="audit_logs")
    related_version = relationship("DocumentVersion", foreign_keys=[related_version_id])
