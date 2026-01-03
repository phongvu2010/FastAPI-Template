from .models import AuditLog, User
import hashlib


def calculate_sha256_hash(file_data_or_path, is_file_path=False):
    """Tính Hash SHA-256 cho file hoặc file path."""
    sha256_hash = hashlib.sha256()

    if is_file_path:
        with open(file_data_or_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
    else:
        # Xử lý File Upload (File.chunks())
        for chunk in file_data_or_path.chunks():
            sha256_hash.update(chunk)

    return sha256_hash.hexdigest()


def create_audit_log(document, actor, action, details=None):
    """Hàm tiện ích Ghi log Bắt buộc và Không thể Sửa/Xóa (AuditLog)."""
    if details is None:
        details = {}

    AuditLog.objects.create(
        document=document, actor=actor, action=action, details=details
    )


def is_allowed_role(user: User, required_role: str) -> bool:
    """Kiểm tra Phân quyền RBAC đơn giản."""
    # [cite_start]Logic trong views.py kiểm tra if request.user.role == 'CHECKER' [cite: 14]
    return user.is_authenticated and user.role == required_role
