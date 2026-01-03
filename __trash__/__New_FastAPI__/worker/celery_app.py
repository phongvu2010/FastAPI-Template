from celery import Celery
from ..core.config import settings # Giả định file config.py tồn tại


# Khởi tạo Celery
# Tên ứng dụng (tùy chọn, dùng để phân biệt các ứng dụng Celery)
celery_app = Celery(
    "secure_doc_flow_worker",
    # Broker: Nơi Celery nhận các lệnh/tasks
    broker=settings.CELERY_BROKER_URL,
    # Backend: Nơi Celery lưu trữ kết quả của các tasks (thường là Redis hoặc Database)
    backend=settings.CELERY_RESULT_BACKEND
)

# Cấu hình Celery
celery_app.conf.update(
    # Tự động tìm kiếm các tasks trong modules 'tasks'
    # Đảm bảo tasks.py được đặt trong thư mục worker
    include=['app.worker.tasks'],

    # Cấu hình Serialization (JSON là chuẩn và an toàn)
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],

    # Cấu hình Timezone
    timezone='Asia/Ho_Chi_Minh',
    enable_utc=True,

    # Một số cài đặt an toàn khác
    task_acks_late=True, # Chỉ xác nhận task sau khi đã hoàn thành
    worker_prefetch_multiplier=1, # Xử lý 1 task 1 lần
)

# GIẢ ĐỊNH: Định nghĩa cấu hình tối thiểu trong app/core/config.py
# (Bạn cần tạo file này và thiết lập các biến môi trường thực tế)
class Settings:
    CELERY_BROKER_URL: str = "redis://localhost:6379/0" # Hoặc RabbitMQ
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

settings = Settings()
