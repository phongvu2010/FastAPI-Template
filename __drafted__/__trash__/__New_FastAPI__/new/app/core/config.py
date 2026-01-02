from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, SecretStr
from typing import Optional

# Lưu ý: Cần cài đặt thư viện này: pip install pydantic-settings


class Settings(BaseSettings):
    """
    Class quản lý cấu hình ứng dụng, đọc biến từ môi trường
    hoặc file .env (theo quy ước của Pydantic).
    """

    # Cấu hình Pydantic v2: Thiết lập file .env là nguồn chính
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore' # Bỏ qua các biến không được định nghĩa trong class
    )

    # =======================================================================
    # 1. Cấu hình Chung
    # =======================================================================
    PROJECT_NAME: str = "SecureDocFlow"

    # Cấu hình môi trường (ví dụ: 'production', 'development', 'testing')
    ENVIRONMENT: str = Field(default="development")

    # =======================================================================
    # 2. Cấu hình Database (PostgreSQL)
    # =======================================================================
    # Field[SecretStr] được khuyến nghị cho các giá trị nhạy cảm
    DATABASE_URL: SecretStr = Field(
        ...,
        description="URL kết nối cơ sở dữ liệu (vd: postgresql://user:pass@host:port/dbname)"
    )

    # =======================================================================
    # 3. Cấu hình Bảo mật và Xác thực (dùng cho JWT)
    # =======================================================================
    SECRET_KEY: SecretStr = Field(
        ...,
        description="Key bí mật dùng để ký JWT Token. Rất quan trọng!"
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 ngày

    # Cấu hình cho Signed URL Token (dùng trong storage_service)
    SIGNED_URL_SECRET: SecretStr = Field(
        "DEFAULT_SIGNED_URL_SECRET_DEV_ONLY",
        description="Key bí mật dùng để ký Signed URL Token. Cần khác SECRET_KEY."
    )

    # Cấu hình Storage
    STORAGE_TYPE: str = Field(
        "LOCAL",
        description="Loại storage: LOCAL, S3, GCS (cho MinIO/Google Cloud Storage)"
    )

    LOCAL_STORAGE_DIR: str = Field(
        "uploads/",
        description="Thư mục vật lý cho Local Storage"
    )

    # =======================================================================
    # 4. Cấu hình Celery/Worker
    # =======================================================================
    # Giả định dùng Redis cho cả Broker và Backend
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # =======================================================================
    # 5. Cấu hình Tích hợp bên ngoài (Google SSO)
    # =======================================================================
    GOOGLE_CLIENT_ID: Optional[SecretStr] = Field(None)
    GOOGLE_CLIENT_SECRET: Optional[SecretStr] = Field(None)

# Khởi tạo instance của Settings để sử dụng trong toàn bộ dự án
settings = Settings()
