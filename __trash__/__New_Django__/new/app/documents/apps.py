from django.apps import AppConfig


class DocumentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    # Đặt tên ứng dụng chính xác
    name = "documents"
    verbose_name = "Quản lý Hồ sơ & Chữ ký số"
