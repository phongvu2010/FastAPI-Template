import os
from pydantic import Field

class Settings(BaseSettings):
    """
    Quản lý toàn bộ cấu hình và biến môi trường của ứng dụng.
    """

    DESCRIPTION: str = ""

    # Secret để ký state CSRF (Nên khác JWT_SECRET)
    STATE_SECRET_KEY: str
    # STATE_SECRET_KEY: str = Field(default="", alias="STATE_SECRET_KEY")


# class Settings(BaseSettings):
#     """
#     Class định nghĩa các biến cấu hình ứng dụng, lấy giá trị
#     theo thứ tự ưu tiên:
#     1. Biến môi trường (Environment Variables)
#     2. File .env (Nếu được bật)
#     3. Giá trị mặc định (Default values)
#     """

#     # Celery
#     REDIS_URI: str = "redis://localhost:6379/0"

#     # --- File Storage ---
#     # Thư mục lưu trữ hồ sơ upload
#     UPLOAD_DIR: str = Field(default="uploaded_files", alias="UPLOAD_DIR")

#     @computed_field
#     @property
#     def ABS_UPLOAD_DIR(self) -> str:
#         """Đường dẫn tuyệt đối đến thư mục upload."""
#         path = os.path.join(os.getcwd(), self.UPLOAD_DIR)
#         os.makedirs(path, exist_ok=True)  # Tự động tạo thư mục nếu chưa có
#         return path
