from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Các lựa chọn cho vai trò
    ROLE_CHOICES = (
        ('SENDER', 'Người gửi'),
        ('CHECKER', 'Người kiểm tra'),
        ('MANAGER', 'Người ký'),
        ('ADMIN', 'Quản trị viên'),
    )

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='SENDER',
        verbose_name="Vai trò nghiệp vụ"
    )

    # Sử dụng email làm USERNAME_FIELD cho SSO
    email = models.EmailField(unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username'] # vẫn yêu cầu username khi tạo superuser

    def __str__(self):
        return self.email
