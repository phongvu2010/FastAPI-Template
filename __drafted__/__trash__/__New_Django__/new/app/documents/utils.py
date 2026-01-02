from .models import AuditLog

def create_audit(actor, action, document=None, document_version=None, details=None):
    """
    Hàm helper để tạo AuditLog nhất quán.
    """
    AuditLog.objects.create(
        actor=actor,
        action=action,
        document=document,
        document_version=document_version,
        details=details or {}
    )
