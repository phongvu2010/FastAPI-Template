from fastapi import Request

from ...core.user_registry import user_registry
from ...db.database import AsyncSessionLocal
from .dependencies import get_validated_user_or_none


# 1. Định nghĩa hàm loader cho Core
async def user_loader_for_core(request: Request):
    """
    Hàm này được Core gọi khi có lỗi xảy ra.
    Nó tự mở DB session, check cookie và trả về User object.
    """
    token = request.cookies.get(settings.COOKIE_NAME)
    if not token:
        return None
    
    # Tự tạo session scope vì Exception Handler không có Depends(get_db)
    async with AsyncSessionLocal() as db:
        return await get_validated_user_or_none(db, token)

# 2. Đăng ký hàm này vào Core Registry
# Khi file này được import bởi module_loader, dòng lệnh này sẽ chạy ngay.
user_registry.register_loader(user_loader_for_core)
