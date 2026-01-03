SECRET_KEY = 'django-insecure-5b73xfaihj4=)73+^e3jdqhwxa*%i-nn3a3**w13nvvos07p5j'

INSTALLED_APPS = [
    "accounts",
    "documents",
    # "django_allauth", # Sẽ thêm sau khi cấu hình cơ bản hoàn tất
    # "celery", # Sẽ thêm sau
    "rest_framework",
    "rest_framework_simplejwt", # Thêm JWT
    "django.contrib.sites", # allauth cần site framework
    
    "allauth.socialaccount.providers.google", # Thêm Google Provider
]

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': 'digital_signature_db',  # Tên database bạn đã tạo ở trên
#         'USER': 'postgres',              # Tên user của PostgreSQL (thường là 'postgres')
#         'PASSWORD': 'your_postgres_password', # Mật khẩu của user đó
#         'HOST': 'localhost',             # Hoặc địa chỉ IP nếu database ở server khác
#         'PORT': '5432',                  # Port mặc định của PostgreSQL
#     }
# }



# Định nghĩa Custom User Model
AUTH_USER_MODEL = 'accounts.CustomUser'

# Cấu hình lưu trữ File (đường dẫn tuyệt đối tới thư mục media)
import os
MEDIA_URL = "/media/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Cấu hình DRF sử dụng JWT làm cơ chế xác thực mặc định
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated', # Mặc định yêu cầu đăng nhập
    )
}

from datetime import timedelta

# Cấu hình JWT (Ví dụ: Token hết hạn sau 5 giờ)
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True, # Tăng cường bảo mật
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': SECRET_KEY, # Sử dụng SECRET_KEY của Django
    # Thêm thông tin Role vào Token Payload để kiểm tra phân quyền nhanh hơn
    'USER_ID_FIELD': 'id',
    'USER_AUTHENTICATION_RULE': 'rest_framework_simplejwt.authentication.default_user_authentication_rule',
    'AUTH_HEADER_TYPES': ('Bearer',),
}

SITE_ID = 1 # ID của Site hiện tại

# Cấu hình Allauth
ACCOUNT_AUTHENTICATION_METHOD = "email" # Dùng email để đăng nhập
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False # Không yêu cầu username
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
LOGIN_REDIRECT_URL = '/' # Redirect sau đăng nhập (sẽ được thay thế bằng logic API)

# Cấu hình Social Account (Google)
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}

# Cấu hình Allauth sử dụng các Adapters tùy chỉnh
ACCOUNT_ADAPTER = 'accounts.adapter.JWTAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapter.CustomSocialAccountAdapter'
