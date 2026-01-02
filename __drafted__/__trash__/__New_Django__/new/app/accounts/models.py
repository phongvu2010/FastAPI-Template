from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid

class User(AbstractUser):
    # username/email managed by Google SSO; require unique email
    email = models.EmailField(unique=True)

    ROLE_CHOICES = [
        ("SENDER", "SENDER"),
        ("CHECKER", "CHECKER"),
        ("MANAGER", "MANAGER"),
        ("ADMIN", "ADMIN"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="SENDER")

    # Vô hiệu hóa username, dùng email làm định danh
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
