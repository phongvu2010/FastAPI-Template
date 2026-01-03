from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User  # Đảm bảo import đúng mô hình User tùy chỉnh của bạn


# Định nghĩa các trường để hiển thị và chỉnh sửa trong Admin
class CustomUserAdmin(UserAdmin):
    # Loại bỏ 'username' khỏi tất cả các chế độ xem

    # 1. Hiển thị danh sách: Thay 'username' bằng 'email'
    list_display = ("email", "first_name", "last_name", "role", "is_staff")

    # 2. Lọc & Tìm kiếm: Tìm kiếm bằng 'email'
    search_fields = ("email", "first_name", "last_name")
    ordering = ("email",)

    # 3. Chỉnh sửa chi tiết (fieldsets)
    # Loại bỏ username khỏi các nhóm trường (fieldsets)
    # Ghi đè fieldsets mặc định của UserAdmin
    fieldsets = (
        (None, {"fields": ("email", "password")}),  # Thay thế username bằng email
        # Thêm trường Role tùy chỉnh
        ("Thông tin Cá nhân", {"fields": ("first_name", "last_name", "role")}),
        # Giữ lại các trường mặc định (quyền, ngày tháng, v.v.)
        (
            "Quyền hạn",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Ngày tháng quan trọng", {"fields": ("last_login", "date_joined")}),
    )

    # Loại bỏ username khỏi form thêm mới
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "role",
                    "password",
                    "password2",
                ),
            },
        ),
    )


# Đăng ký mô hình User tùy chỉnh với Admin
admin.site.register(User, CustomUserAdmin)
