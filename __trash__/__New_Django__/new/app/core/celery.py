import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

# Khởi tạo Celery instance
app = Celery('core')

# Load task settings from Django settings file
# namespace='CELERY' means all celery-related configuration keys
# should have a `CELERY_` prefix in settings.py.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (tasks.py)
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """
    Task mẫu để kiểm tra Celery có hoạt động không.
    """
    print(f"Request: {self.request!r}")
