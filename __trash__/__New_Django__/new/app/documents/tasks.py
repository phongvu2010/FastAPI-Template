from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Max
from documents.models import Document, DocumentVersion, Signature
from documents.utils import create_audit
import hashlib
import time # Dùng cho mục đích mô phỏng

# Task 1: Gửi thông báo (Email/SMS/Websocket - Tạm dùng Email)
@shared_task(name='documents.tasks.send_notification_task', 
             autoretry_for=(Exception,), retry_backoff=5, max_retries=3)
def send_notification_task(recipient_email, subject, message, action, document_id=None):
    """
    Tác vụ gửi thông báo cho các bên liên quan.
    """
    try:
        # Trong môi trường thực tế, logic này phức tạp hơn (dùng mẫu email, HTML, v.v.)
        send_mail(
            subject=f"[Document System] {subject}",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL, # Cần cấu hình trong settings.py
            recipient_list=[recipient_email],
            fail_silently=False,
        )
        
        # Ghi Audit Log cho hành động gửi thông báo (tùy chọn)
        # Nếu cần, bạn phải lấy User object dựa trên email
        print(f"Notification sent successfully to {recipient_email} for action: {action}") 
        
    except Exception as exc:
        # Nếu gửi thất bại, Celery sẽ tự động retry (theo cấu hình @shared_task)
        raise self.retry(exc=exc, countdown=5) 

# Task 2: Xác thực Hash Bất đồng bộ cho File Upload
@shared_task(name='documents.tasks.verify_hash_task', 
             autoretry_for=(Exception,), max_retries=1)
def verify_hash_task(document_version_id):
    """
    Xác thực SHA256 Hash của file sau khi upload (bất đồng bộ).
    """
    try:
        dv = DocumentVersion.objects.get(id=document_version_id)
        
        # Mô phỏng một tác vụ tốn thời gian
        time.sleep(1) 
        
        # Tính lại Hash
        dv.file.open('rb')
        sha256_hash = hashlib.sha256()
        for chunk in dv.file.chunks():
            sha256_hash.update(chunk)
        computed_hash = sha256_hash.hexdigest()
        dv.file.close()

        # So sánh
        if computed_hash == dv.file_hash:
            status = "SUCCESS"
            details = {"result": "Hash confirmed correct"}
        else:
            status = "FAILED"
            details = {"result": "Hash mismatch!", "computed": computed_hash, "stored": dv.file_hash}
            
        # Ghi Audit Log
        create_audit(
            actor=None, # Tác vụ hệ thống
            action=f"ASYNC_HASH_VERIFY_{status}",
            document=dv.document,
            document_version=dv,
            details=details
        )
        
        if status == "FAILED":
             # Kích hoạt thông báo cảnh báo cho Admin/Manager
             print(f"ALERT: Hash mismatch detected for DocumentVersion ID {document_version_id}")

    except DocumentVersion.DoesNotExist:
        print(f"Error: DocumentVersion ID {document_version_id} not found.")

# Task 3: Tác vụ định kỳ (dùng cho CELERY_BEAT)
@shared_task(name='documents.tasks.verify_all_hashes')
def verify_all_hashes():
    """
    Task chạy định kỳ để kiểm tra lại hash của tất cả các phiên bản cuối cùng (tốn thời gian).
    """
    print("Starting daily hash verification for all final documents...")
    
    # Lấy ra phiên bản mới nhất của mỗi Document đã hoàn thành
    latest_versions = DocumentVersion.objects.filter(
        document__status__in=["COMPLETED_INTERNAL", "COMPLETED_EXTERNAL"]
    ).annotate(
        max_version=Max('document__versions__version_number')
    ).filter(
        version_number=models.F('max_version')
    )

    for dv in latest_versions:
        # Gửi task kiểm tra cho từng phiên bản
        verify_hash_task.delay(str(dv.id)) 
        
    print(f"Dispatched verification for {latest_versions.count()} documents.")


# from .models import Document  # Đảm bảo đã import Document

# @shared_task
# def send_notification_task(document_id, action):
#     """
#     Task bất đồng bộ để gửi email thông báo sau khi thay đổi trạng thái.
#     Sử dụng các cấu hình email từ settings.py.
#     """
#     try:
#         # Lấy Hồ sơ và User tạo ra nó (giảm thiểu DB query)
#         document = Document.objects.select_related("created_by").get(pk=document_id)

#         # --- Xác định người nhận chung ---
#         # Người nộp (Sender) và Manager (đã cấu hình trong settings.MANAGER_EMAIL)
#         recipient_list = [document.created_by.email, settings.MANAGER_EMAIL]

#         # --- Xác định nội dung (Subject & Message) dựa trên Action ---
#         if action == "APPROVED":
#             subject = f"[Hồ sơ số {document_id}] Đã được Duyệt (Ký Nháy)"
#             message = (
#                 f"Hồ sơ '{document.title}' của bạn đã được CHECKER duyệt (Ký Nháy). "
#                 f"Tài liệu hiện đang ở trạng thái **APPROVED_FOR_SIGNING** và chờ MANAGER ký chính. "
#                 f"Người nộp: {document.created_by.email}"
#             )

#         elif action == "COMPLETED_INTERNAL":
#             subject = f"[Hồ sơ số {document_id}] Đã Ký Chính Nội bộ"
#             message = (
#                 f"Hồ sơ '{document.title}' đã hoàn tất quy trình ký chính nội bộ. "
#                 f"Trạng thái: **COMPLETED_INTERNAL**. "
#                 f"Bạn có thể download phiên bản đã ký từ hệ thống."
#             )

#         elif action == "COMPLETED_EXTERNAL":
#             # BỔ SUNG: Xử lý thông báo khi file đã được ký ngoài và upload
#             subject = f"[Hồ sơ số {document_id}] Đã Ký Chính Bên ngoài"
#             message = (
#                 f"Hồ sơ '{document.title}' đã được MANAGER upload file đã ký bởi CA ngoài. "
#                 f"Trạng thái: **COMPLETED_EXTERNAL**. "
#                 f"Phiên bản mới nhất đã được lưu trữ trong hệ thống."
#             )

#         else:
#             return  # Bỏ qua nếu action không hợp lệ

#         # Gửi mail
#         send_mail(
#             subject,
#             message,
#             settings.DEFAULT_FROM_EMAIL,  # Người gửi (Đã cấu hình trong settings)
#             recipient_list,
#             fail_silently=False,  # Bắt exception nếu việc gửi mail thất bại
#         )
#         print(f"Gửi thông báo thành công cho Hồ sơ {document_id} - Hành động {action}")
#     except Document.DoesNotExist:
#         # Xử lý trường hợp Document bị xóa giữa chừng
#         print(f"Lỗi: Không tìm thấy Hồ sơ ID {document_id}. Task bị hủy.")
#     except Exception as e:
#         # Xử lý các lỗi khác (ví dụ: lỗi kết nối SMTP)
#         # Celery sẽ tự động retry nếu task bị lỗi, trừ khi bạn cấu hình khác.
#         print(f"Lỗi gửi thông báo cho Hồ sơ {document_id}: {e}")
#         # Quan trọng: Cần raise lại lỗi để Celery biết và retry
#         raise
