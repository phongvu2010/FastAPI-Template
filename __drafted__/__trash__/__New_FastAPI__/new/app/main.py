from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Import cấu hình
from .core.config import settings

# Import các Routers đã tạo
from .api.v1 import documents
# Giả định: router cho người dùng (Auth/RBAC)
# from .api.v1 import users

from .services.storage_service import AbstractStorageService, LocalStorageService 
from .services.document_service import DocumentService

# Khởi tạo Service Instances 
document_service_instance = DocumentService()
if settings.STORAGE_TYPE == "LOCAL":
    storage_service_instance = LocalStorageService()
    
# Dependency Functions
def get_document_service() -> DocumentService:
    return document_service_instance

def get_storage_service() -> AbstractStorageService:
    return storage_service_instance

# =======================================================================
# 1. Khởi tạo FastAPI App
# =======================================================================

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Hàm xử lý sự kiện khi ứng dụng khởi động và tắt.
    Có thể dùng để: kết nối/ngắt kết nối DB, khởi tạo Celery, tải Models/Keys.
    """
    print("Ứng dụng SecureDocFlow đang khởi động...")
    # TODO: Khởi tạo kết nối DB/Celery nếu cần kiểm tra sớm
    yield
    print("Ứng dụng SecureDocFlow đang tắt...")


# Khởi tạo ứng dụng chính
app = FastAPI(
    title=settings.PROJECT_NAME,
    version="v1.0.0",
    openapi_url="/api/v1/openapi.json", # Định nghĩa URL cho OpenAPI spec
    docs_url="/api/v1/docs",            # Định nghĩa URL cho Swagger UI
    lifespan=lifespan # Áp dụng lifespan context manager
)


# =======================================================================
# 2. Middlewares
# =======================================================================

# Cấu hình CORS (quan trọng cho Frontend gọi API)
# Tùy chỉnh `origins` theo domain Frontend của bạn
origins = [
    "http://localhost:3000", # Ví dụ Frontend chạy trên cổng này
    "http://127.0.0.1:3000",
    # Thêm domain production của bạn khi triển khai
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =======================================================================
# 3. Gộp các Routers (API Endpoints)
# =======================================================================

# # Router cho Tài liệu (Documents)
# app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])

# # Router riêng cho Download Handler
# app.include_router(documents.download_router, prefix="/api/v1", tags=["Download"])

from .api.v1.router import api_v1_router

app.include_router(api_v1_router, prefix="/api/v1")

# Giả định: Router cho Người dùng (Users/Auth)
# app.include_router(
#     users.router,
#     prefix="/api/v1",
#     tags=["Users & Authentication"]
# )

# TODO: Thêm các routers khác như admin.py (nếu có)


# =======================================================================
# 4. Route kiểm tra sức khỏe (Health Check)
# =======================================================================

@app.get("/health", tags=["System"], summary="Kiểm tra trạng thái hệ thống")
async def health_check():
    """Kiểm tra ứng dụng có đang hoạt động không."""
    return {"status": "ok", "project": settings.PROJECT_NAME}

# =======================================================================

# Khởi chạy bằng: uvicorn app.main:app --reload
