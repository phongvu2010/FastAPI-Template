from fastapi import APIRouter

# Import các routers con
from . import documents
# from . import users # Sẽ tạo dưới đây
# from . import admin # Sẽ tạo dưới đây

# Router chính cho version v1
api_v1_router = APIRouter()

# Gộp các routers con vào router chính
api_v1_router.include_router(documents.router)
api_v1_router.include_router(documents.download_router)
# api_v1_router.include_router(users.router) 
# api_v1_router.include_router(admin.router)
