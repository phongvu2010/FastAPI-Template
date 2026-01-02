from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid

# Model Document: Quản lý hồ sơ tổng thể
class Document(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=512)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_documents"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    STATUS_CHOICES = [
        ("PENDING", "Chờ duyệt"),
        ("REJECTED", "Bị từ chối"),
        ("APPROVED_FOR_SIGNING", "Đã duyệt, chờ ký"),
        ("COMPLETED_INTERNAL", "Hoàn thành (Ký nội bộ)"),
        ("COMPLETED_EXTERNAL", "Hoàn thành (Ký ngoài)"),
    ]
    status = models.CharField(max_length=40, default="PENDING", choices=STATUS_CHOICES)

    approved_version = models.ForeignKey(
        "DocumentVersion",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+"
    )
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["status"])]
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

# Model DocumentVersion: Quản lý các phiên bản file
class DocumentVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="versions"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to="documents/%Y/%m/%d/")
    file_hash = models.CharField(max_length=128, db_index=True)
    version_number = models.IntegerField()
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("document", "version_number")
        ordering = ["-version_number"]

    def __str__(self):
        return f"{self.document.title} (v{self.version_number})"

# Model Signature: Lưu vết chữ ký
class Signature(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.CASCADE,
        related_name="signatures"
    )
    signer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    SIG_TYPES = [("INTERNAL", "INTERNAL"), ("EXTERNAL", "EXTERNAL")]
    sig_type = models.CharField(max_length=20, choices=SIG_TYPES)

    signature_blob = models.BinaryField()
    public_key = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    meta = models.JSONField(default=dict, blank=True)

# Model AuditLog: Ghi vết (Bất biến)
class AuditLog(models.Model):
    id = models.BigAutoField(primary_key=True)
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    action = models.CharField(max_length=100)
    document = models.ForeignKey(
        Document,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    document_version = models.ForeignKey(
        DocumentVersion,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    details = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]

    def delete(self, *args, **kwargs):
        raise Exception("Audit log is immutable")
