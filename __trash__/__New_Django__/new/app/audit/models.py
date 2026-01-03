from django.db import models
from django.utils import timezone
from documents.models import Document, User # Import các mô hình từ document_app

# --- 3. AUDIT LOG MODEL ---

# # AuditLog Model
# class AuditLog(models.Model):
#     document = models.ForeignKey(Document, on_delete=models.CASCADE)
#     actor = models.ForeignKey(User, on_delete=models.PROTECT)
#     action = models.CharField(
#         max_length=50
#     )  # Ví dụ: UPLOAD, SIGNED_INITIALLY, REJECTED, HASH_VERIFIED_FAIL
#     timestamp = models.DateTimeField(auto_now_add=True)
#     details = models.JSONField(default=dict)  # Lý do từ chối, IP, lỗi bảo mật
#     # Thiết lập ReadOnly thông qua permission/admin config 


class AuditLog(models.Model):
    """
    Nhật ký Kiểm toán không thể sửa/xóa (ReadOnly).
    Ghi lại mọi thay đổi trạng thái, hành động quan trọng, hoặc lỗi bảo mật.
    """
    document = models.ForeignKey(
        Document, 
        on_delete=models.PROTECT, 
        related_name='audit_records',
        verbose_name='Hồ sơ liên quan'
    )
    
    actor = models.ForeignKey(
        User, 
        on_delete=models.PROTECT, 
        null=True,
        blank=True,
        verbose_name='Người thực hiện'
    )
    
    action = models.CharField(
        max_length=100, 
        verbose_name='Hành động',
        help_text='Ví dụ: UPLOAD, SIGNED_INITIALLY, REJECTED, HASH_VERIFIED_FAIL.'
    )
    
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    
    details = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Chi tiết log',
        help_text='Bao gồm lý do từ chối, lỗi bảo mật, IP, v.v.'
    )

    class Meta:
        verbose_name = 'Nhật ký Kiểm toán'
        verbose_name_plural = 'Nhật ký Kiểm toán'
        # VÔ HIỆU HÓA default permissions (add, change, delete)
        default_permissions = () 
        # Chỉ cho phép quyền xem
        permissions = [
            ('view_auditlog', 'Can view audit log records'),
        ]
        ordering = ['timestamp']
        
    def __str__(self):
        return f"{self.action} on {self.document.title} by {self.actor.email if self.actor else 'System'}"

    # Ngăn chặn việc xóa/sửa record bằng cách ghi đè save/delete
    def save(self, *args, **kwargs):
        # Nếu đã tồn tại (pk is not None), không cho phép sửa
        if self.pk:
            raise Exception("Audit Log không thể sửa đổi sau khi tạo.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise Exception("Audit Log không thể bị xóa.")
