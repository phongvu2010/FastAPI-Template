from .celery_app import celery_app
from typing import Dict, Any, Optional
import time
import uuid

# GIẢ ĐỊNH: Import Notification Service (chưa viết)
# import notification_service # Ví dụ: from ..services.notification_service import notification_service

# GIẢ ĐỊNH: Import Logic DB (chưa thể dùng get_db trong Celery)
# Trong môi trường thực tế, Celery task cần tạo DB session riêng:
from sqlalchemy.orm import Session
from ..db.base import SessionLocal
from ..db import models, schemas
from ..services.document_service import document_service # Giả sử cần service để cập nhật trạng thái


# =======================================================================
# 1. Background Task: Gửi Email / Notification
# =======================================================================

@celery_app.task(name="send_notification")
def send_notification_task(
    recipient_email: str,
    subject: str,
    body: str,
    document_id: Optional[str] = None
) -> str:
    """
    Tác vụ bất đồng bộ để gửi email hoặc thông báo push.
    """
    # Gợi ý logic:
    # 1. Kết nối với dịch vụ Email/SMS (ví dụ: SendGrid, Mailgun)
    # 2. notification_service.send_email(...)

    print(f"[{time.strftime('%H:%M:%S')}] Đang gửi thông báo cho: {recipient_email}")
    # Giả lập thời gian trễ
    time.sleep(2)
    print(f"[{time.strftime('%H:%M:%S')}] Gửi thông báo thành công. Document ID: {document_id}")

    return f"Notification sent to {recipient_email}"


# =======================================================================
# 2. Background Task: Kiểm tra Hash nền (Tùy chọn)
# =======================================================================

@celery_app.task(name="background_hash_verification")
def background_hash_verification_task(
    document_version_id_str: str,
    expected_hash: str
) -> bool:
    """
    Tác vụ kiểm tra lại Hash của file sau khi upload (để tăng cường bảo mật).
    - Đọc lại file từ storage.
    - Tính toán hash và so sánh với hash trong DB.
    """
    document_version_id = uuid.UUID(document_version_id_str)

    # Celery task cần tự quản lý DB Session
    db: Session = SessionLocal()
    try:
        # Lấy DocumentVersion
        doc_version = db.get(models.DocumentVersion, document_version_id)
        if not doc_version:
            return False

        # TODO: Cần logic đọc file từ Storage và tính hash lại.
        # HASH_SAU_KHI_DOC = storage_service.recompute_hash(doc_version.file_path)

        # Giả lập kết quả
        is_match = (expected_hash == doc_version.file_hash)

        # Nếu không khớp, ghi AuditLog lỗi
        if not is_match:
            # Ghi Log lỗi và có thể cập nhật trạng thái Document (nếu cần)
            pass

        return is_match

    finally:
        db.close()

# Ví dụ về cách gọi task từ DocumentService (khi upload):
# tasks.send_notification_task.delay(user.email, "Tài liệu mới", "Bạn đã upload thành công.")
# tasks.background_hash_verification_task.delay(new_version.id, new_version.file_hash)
