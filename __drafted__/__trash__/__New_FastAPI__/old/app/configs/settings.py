import secrets

from pathlib import Path
from pydantic import PostgresDsn
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from urllib import parse

class Settings(BaseSettings):
    """Lớp Cấu hình trung tâm, đọc các biến từ file .env"""
    # Cấu hình Database
    DB_USER: str = "docmanager"
    DB_PASSWORD: str = "secretpassword"
    DB_NAME: str = "document_db"
    DB_HOST: str = "db"
    DB_PORT: int = 5432

    @computed_field  # type: ignore[misc]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme = "postgresql+psycopg2",
            username = self.DB_USER,
            password = parse.quote_plus(self.DB_PASSWORD),
            host = self.DB_HOST,
            port = self.DB_PORT,
            path = self.DB_NAME
        )

    # Cấu hình Redis (Celery Broker)
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379

    # Đường dẫn lưu trữ file (Trong Docker Container)
    # Pydantic sẽ tự động chuyển đổi string từ .env thành đối tượng Path
    BASE_STORAGE_PATH: Path = Path("/code/app_storage")

    # --- Cấu hình Bảo mật ---
    # Cần tạo một chuỗi ngẫu nhiên (Vd: openssl rand -hex 32)
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 1 ngày

    # Cấu hình Pydantic
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False  # Không phân biệt chữ hoa-thường
    )

# Tạo một instance duy nhất (singleton)
settings = Settings()
