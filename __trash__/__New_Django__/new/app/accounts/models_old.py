from django.contrib.auth.models import BaseUserManager
from django.core.validators import MinValueValidator
from django.utils.text import slugify
import hashlib
from io import BytesIO

# --- 1. USER & AUTHENTICATION MODELS ---


class UserRole(models.TextChoices):
    """
    Vai trò cho phân quyền RBAC.
    """

    SENDER = "SENDER", "Người Gửi/Nộp Hồ sơ"
    CHECKER = "CHECKER", "Người Kiểm tra/Duyệt nháy"
    MANAGER = "MANAGER", "Quản lý/Người Ký Chính"
    ADMIN = "ADMIN", "Quản trị Hệ thống"


class UserManager(BaseUserManager):
    """
    Manager tùy chỉnh cho mô hình User, sử dụng email làm định danh duy nhất (SSO).
    """

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email là bắt buộc")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault(
            "role", UserRole.ADMIN
        )  # Siêu quản trị mặc định là ADMIN

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser phải có is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser phải có is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Mô hình User tùy chỉnh, loại bỏ username, sử dụng email làm định danh chính.
    """

    username = None

    # Trường email: dùng làm định danh chính (UNIQUE)
    email = models.EmailField(
        "Địa chỉ email", unique=True, help_text="Email được cung cấp từ Google SSO."
    )

    # Trường Role: Rất quan trọng cho logic phân quyền
    role = models.CharField(
        max_length=10,
        choices=UserRole.choices,
        default=UserRole.SENDER,
        verbose_name="Vai trò",
        help_text="Vai trò quyết định quyền truy cập (RBAC).",
    )

    objects = UserManager()  # GÁN MANAGER TÙY CHỈNH

    # Thiết lập email làm trường định danh chính để đăng nhập
    USERNAME_FIELD = "email"
    # Loại bỏ yêu cầu nhập email khi tạo superuser
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"

    def __str__(self):
        return self.email
