from django.http import JsonResponse
from django.db import connection

def health_check(request):
    try:
        # Kiểm tra kết nối DB
        connection.ensure_connection()
        db_status = "OK"
    except Exception:
        db_status = "FAIL"

    # Kiểm tra Redis/Celery (có thể phức tạp hơn)
    # redis_status = "OK" # Giả định

    if db_status == "OK":
        return JsonResponse({"status": "healthy", "database": db_status}, status=200)
    else:
        return JsonResponse({"status": "unhealthy", "database": db_status}, status=503)
