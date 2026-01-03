# 1. Cấu hình ALLOWED_HOSTS
if DEBUG:
    # Cho phép truy cập từ localhost, 127.0.0.1, và container
    ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1", "web"]
else:
    # Production: Đảm bảo chỉ tên miền thật được phép
    # Bạn nên đọc giá trị này từ biến môi trường
    ALLOWED_HOSTS = config(
        "ALLOWED_HOSTS", 
        # Sử dụng cast để chuyển chuỗi (vd: 'host1, host2') thành list
        cast=lambda v: [s.strip() for s in v.split(",")], 
        default="docs.bacbinh.vn"
    )

# 2. Cấu hình Bảo mật cho Production
if not DEBUG:
    # Bắt buộc chuyển đổi HTTP sang HTTPS
    SECURE_SSL_REDIRECT = True

    # Giúp bảo vệ Cookies (Session và CSRF)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Cấu hình HSTS (khuyến nghị cho bảo mật cao)
    # SECURE_HSTS_SECONDS = 31536000 # 1 năm
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_HSTS_PRELOAD = True

INSTALLED_APPS = [
    # "django_celery_results", # Nếu bạn dùng DB làm result backend

    # Apps của bạn
    "accounts.apps.AccountsConfig",
    # "documents.apps.DocumentsConfig",
    # "audit.apps.AuditConfig",
]

MIDDLEWARE = [
    'whitenoise.middleware.WhiteNoiseMiddleware',
]



# # --- Media & Static Files ---
# # ĐƯỜNG DẪN DÀNH CHO WhiteNoise: Nơi Django/Collectstatic thu thập file
# # STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
# STATIC_ROOT = BASE_DIR / "staticfiles" # ⬅️ Thư mục để collectstatic

# # # Các file PDF sẽ được lưu ở đây, được map tới Docker Volume
# # Cấu hình Media (File người dùng upload: PDF)
# MEDIA_URL = "media/"
# # ĐƯỜNG DẪN DÀNH CHO File Upload: Trỏ tới volume đã map
# # MEDIA_ROOT = os.path.join(BASE_DIR, "mediafiles")
# MEDIA_ROOT = BASE_DIR / "storages/mediafiles"



# # 3. Cấu hình email và username (Bắt buộc phải có để Allauth biết cách xử lý)
# # ACCOUNT_EMAIL_REQUIRED = True
# # ACCOUNT_USERNAME_REQUIRED = False
# ACCOUNT_USER_MODEL_USERNAME_FIELD = None  # Rất quan trọng, xác nhận không dùng username

# LOGIN_REDIRECT_URL = "/"  # Trang chuyển hướng sau khi đăng nhập thành công

# # Cấu hình Google Provider
# SOCIALACCOUNT_PROVIDERS = {
#     "google": {
#         "SCOPE": [
#             "profile",
#             "email",
#         ],
#         "AUTH_PARAMS": {
#             "access_type": "online",
#         },
#     }
# }

# # Google OAuth Credentials
# # Đọc biến môi trường cho Google
# SOCIALACCOUNT_GOOGLE_CLIENT_ID = config("GOOGLE_CLIENT_ID")
# SOCIALACCOUNT_GOOGLE_CLIENT_SECRET = config("GOOGLE_CLIENT_SECRET")




# # # --- Custom App Settings ---
# # Cấu hình Người quản lý chung cho Thông báo
# # # Địa chỉ Email của Manager (Dùng cho logic thông báo trong tasks.py)
# MANAGER_EMAIL = config("MANAGER_EMAIL", default="manager@yourcompany.com")





# # Giá trị 1: Worker chỉ xử lý 1 task tại một thời điểm. Đảm bảo công bằng và tránh worker bị nghẽn.
# CELERY_WORKER_PREFETCH_MULTIPLIER = 1
# # Cấu hình Giới hạn Thời gian cho Task

# Giới hạn thời gian cứng (Hard Time Limit): Celery sẽ kill worker ngay lập tức sau 300 giây.
# Nếu quá trình ký số quá lâu (ví dụ: file > 100MB), nó sẽ bị hủy.
# CELERY_TASK_TIME_LIMIT = 300 

# Giới hạn thời gian mềm (Soft Time Limit): Gửi tín hiệu đến task sau 290 giây để task tự thoát (graceful shutdown).
# CELERY_TASK_SOFT_TIME_LIMIT = 290




# # import os

# # from datetime import timedelta  # Cần cho Celery Beat (nếu dùng)

# # # Cho phép nhiều hosts (trong Prod cần thay '*')
# # ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="*").split(",")

# # # Giảm timeout để phát hiện lỗi sớm hơn (tùy chọn)
# # # BROKER_TRANSPORT_OPTIONS = {"visibility_timeout": 3600}

# # # --- Email Configuration (Dùng cho Celery Tasks) ---
# # EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# # EMAIL_HOST = config("EMAIL_HOST")
# # EMAIL_PORT = config("EMAIL_PORT", cast=int)
# # # Sử dụng bool() để ép kiểu từ config string
# # EMAIL_USE_TLS = config("EMAIL_USE_TLS", cast=bool, default=False)
# # EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool, default=False)
# # # Khóa xác thực
# # EMAIL_HOST_USER = config("EMAIL_HOST_USER")
# # EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
# # # Địa chỉ email mặc định (người gửi)
# # DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL")
