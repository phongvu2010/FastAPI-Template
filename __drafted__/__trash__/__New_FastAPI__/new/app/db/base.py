from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from typing import Generator


# GIẢ ĐỊNH: Import cấu hình (nên được định nghĩa trong app/core/config.py)
# Chúng ta sẽ giả định Settings class có attribute `DATABASE_URL`
class Settings:
    # URL kết nối PostgreSQL (sử dụng asyncpg nếu muốn AsyncSession)
    # Ví dụ: postgresql://user:password@host:port/dbname
    # Ở đây chúng ta dùng driver mặc định cho sync (psycopg2)
    DATABASE_URL = "postgresql://user:password@localhost:5432/secure_doc_flow"

settings = Settings()
# Lưu ý: Trong thực tế, bạn sẽ dùng 'from ..core.config import settings'

# --- 1. Khởi tạo Engine và Session ---

# Khởi tạo SQLAlchemy Engine
# `pool_pre_ping=True` giúp kiểm tra kết nối còn hoạt động không trước khi sử dụng
# `echo=True` (tùy chọn) để in ra các câu lệnh SQL (chỉ nên dùng khi dev)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # echo=True # Tùy chọn: Bật để xem SQL logs
)

# Khởi tạo SessionLocal (session factory)
# `autocommit=False` và `autoflush=False` là cài đặt chuẩn cho ORM (Unit of Work Pattern)
# `bind=engine` liên kết factory này với Engine đã tạo
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# --- 2. Khởi tạo Base (Model Base Class) ---

# Đây là class cơ sở mà tất cả các Model (trong models.py) sẽ kế thừa.
# Bạn đã dùng nó tạm thời trong models.py, giờ chúng ta định nghĩa nó chính thức.
Base = declarative_base()

# --- 3. Dependency Function (FastAPI) ---

def get_db() -> Generator[Session, None, None]:
    """
    Dependency Injector cho FastAPI.
    Cung cấp một SQLAlchemy Session cho mỗi request và đảm bảo Session được đóng.
    """
    db = SessionLocal()
    try:
        # Trả về session cho code của router/service
        yield db
    finally:
        # Đảm bảo session được đóng, dù có lỗi hay không
        db.close()

# --- 4. Helper function cho Migrations (Alembic) ---

# Alembic cần Base và engine để chạy các migrations
def init_db():
    # Thao tác này sẽ tạo tất cả các bảng dựa trên models.py
    # CHỈ DÙNG KHI DEV/TEST LẦN ĐẦU. TRONG PRODUCTION HÃY DÙNG ALEMBIC MIGRATIONS
    Base.metadata.create_all(bind=engine)
