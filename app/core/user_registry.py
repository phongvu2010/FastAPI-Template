
from fastapi import Request
from typing import Callable, Any, Awaitable, Optional


# Định nghĩa kiểu hàm callback: nhận Request -> trả về User (hoặc None)
UserLoaderCallback = Callable[[Request], Awaitable[Optional[Any]]]


class UserRegistry:
    def __init__(self):
        self._user_loader: Optional[UserLoaderCallback] = None

    def register_loader(self, loader: UserLoaderCallback):
        """
        Module Users sẽ gọi hàm này để đăng ký logic.
        """
        self._user_loader = loader

    async def get_user_from_request(self, request: Request) -> Optional[Any]:
        """
        Core gọi hàm này trong error_page.
        """
        if self._user_loader:
            try:
                # Gọi hàm đã được module đăng ký
                return await self._user_loader(request)
            except Exception:
                # Nếu lỗi DB hoặc logic, trả về None để trang lỗi vẫn hiển thị an toàn
                return None
        return None


# Singleton instance để dùng chung toàn app
user_registry = UserRegistry()
