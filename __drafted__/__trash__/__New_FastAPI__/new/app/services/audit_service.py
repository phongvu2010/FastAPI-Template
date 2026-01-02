from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

# Import models và schemas
from ..db import models, schemas


def create_audit_log(
    db: Session,
    actor: Optional[models.User],
    action: str,
    document: Optional[models.Document] = None,
    document_version: Optional[models.DocumentVersion] = None,
    details: Optional[Dict[str, Any]] = None
) -> models.AuditLog:
    """
    Hàm helper tập trung để tạo AuditLog (Source 126, 198).
    Đảm bảo tất cả các bản ghi đều đi qua hàm này.
    """

    # Tạo đối tượng AuditLog từ Pydantic schema (hoặc trực tiếp)
    # Ở đây chúng ta tạo trực tiếp model để liên kết các object
    db_audit = models.AuditLog(
        actor_id=actor.id if actor else None,
        action=action,
        document_id=document.id if document else None,
        document_version_id=document_version.id if document_version else None,
        details=details or {} # Đảm bảo details không bao giờ là None
    )

    db.add(db_audit)

    # Lưu ý: Hàm này không tự commit.
    # Service gọi nó (ví dụ: document_service) sẽ chịu trách nhiệm commit
    # chung cho toàn bộ giao dịch.
    # Chúng ta có thể flush để lấy ID nếu cần ngay, nhưng ở đây là không cần.
    # db.flush()

    return db_audit

# Chúng ta không cần một class cho service này vì nó chỉ có một hàm helper
# Bạn có thể import trực tiếp `create_audit_log` từ các service khác.
