from django.db import models
from accounts.models import CustomUser

# Định nghĩa hàm để tổ chức thư mục lưu trữ file
def document_file_path(instance, filename):
    # Đường dẫn: media/documents/<doc_id>/<version_id>/<filename>
    return f"documents/{instance.document.id}/{instance.version_number}/{filename}"

class DocumentVersion(models.Model):
    document = models.ForeignKey('Document', related_name='versions', on_delete=models.CASCADE)
    uploader = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    file = models.FileField(upload_to=document_file_path)
    version_number = models.PositiveIntegerField(default=1)

    # Trường quan trọng: Lưu trữ Hash SHA-256 của file
    file_hash = models.CharField(max_length=64, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Đảm bảo chỉ có một phiên bản với cùng một số phiên bản trong một tài liệu
        unique_together = ('document', 'version_number')

    def __str__(self):
        return f"{self.document.title} - V{self.version_number}"

class Document(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Chờ duyệt'),
        ('REJECTED', 'Bị từ chối'),
        ('APPROVED_FOR_SIGNING', 'Đã duyệt, Chờ ký'),
        ('COMPLETED_INTERNAL', 'Đã ký nội bộ, Hoàn tất'),
        ('COMPLETED_EXTERNAL', 'Đã ký ngoài, Hoàn tất'),
        ('TAMPERED', 'Phát hiện can thiệp'), # Đã thêm
    )

    title = models.CharField(max_length=255)
    created_by = models.ForeignKey(CustomUser, related_name='submitted_documents', on_delete=models.PROTECT)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING')

    # Phiên bản đã được Checker duyệt (dùng để khóa Hash)
    approved_version = models.ForeignKey(DocumentVersion, related_name='approved_documents',
                                         on_delete=models.SET_NULL, null=True, blank=True)

    # Chữ ký số nội bộ của hệ thống
    internal_signature = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.status})"

class AuditLog(models.Model):
    # Các hành động quan trọng
    ACTION_CHOICES = (
        ('UPLOAD_NEW_VERSION', 'Tải lên phiên bản mới'),
        ('SIGNED_INITIALLY', 'Ký nháy (Duyệt)'),
        ('REJECTED', 'Từ chối'),
        ('TAMPER_DETECTED', 'Phát hiện can thiệp Hash'),
        ('SIGNED_INTERNAL', 'Ký chính nội bộ'),
        ('SIGNING_ERROR', 'Lỗi tạo chữ ký'),
        # ('HASH_VERIFIED_FAIL', 'Lỗi xác thực Hash'),
        # ('SIGNED_INTERNAL', 'Ký chính nội bộ'),
    )

    document = models.ForeignKey(Document, on_delete=models.CASCADE)
    actor = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)

    # Ghi lại trạng thái cũ/mới nếu có thay đổi
    old_status = models.CharField(max_length=30, null=True, blank=True)
    new_status = models.CharField(max_length=30, null=True, blank=True)

    details = models.TextField(null=True, blank=True) # Lý do từ chối, v.v.

    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.timestamp.strftime('%Y-%m-%d %H:%M')}] {self.actor.email} - {self.action} trên {self.document.title}"
