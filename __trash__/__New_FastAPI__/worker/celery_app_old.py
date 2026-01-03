from celery import Celery

from .configs.settings import settings

# Xây dựng URL cho Broker và Backend
# Chúng ta dùng 2 database khác nhau trên Redis:
# 0: Dùng cho Broker (xếp hàng tác vụ)
# 1: Dùng cho Backend (lưu trữ kết quả tác vụ)
BROKER_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0"
BACKEND_URL = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/1"

# Khởi tạo đối tượng Celery
celery_app = Celery(
    "document_manager",  # Tên của dự án
    broker=BROKER_URL,
    backend=BACKEND_URL,
    include=[
        "app.tasks"  # Chỉ định module chứa các task
    ]
)

# Cấu hình Celery (Tùy chọn)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",

    # Thiết lập múi giờ (rất quan trọng cho các tác vụ định kỳ)
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,

    # Theo dõi trạng thái "STARTED" của task
    task_track_started=True,
)

if __name__ == "__main__":
    celery_app.start()
