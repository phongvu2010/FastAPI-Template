# Sử dụng base image Python 3.11/3.12 (nên dùng phiên bản mới nhất LTS)
FROM python:3.12-slim

# Thiết lập biến môi trường để Python không ghi file .pyc và dùng unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=core.settings

# Thiết lập thư mục làm việc trong container
WORKDIR /app

# Cài đặt các thư viện hệ thống cần thiết cho PostgreSQL client (psycopg2)
# và các thư viện bảo mật (cryptography)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev libffi-dev gcc python3-dev \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Cài đặt các dependencies hệ thống cần thiết (ví dụ: cho pyhanko)
# RUN apt-get install -y libssl-dev (Thêm các thư viện hệ thống nếu pyhanko cần)

# # Tạo thư mục lưu trữ bên trong container.
# # Thư mục này được map tới Volume 'storage_volume'
# RUN mkdir -p /storages && chown -R 1000:1000 /storages

# Sao chép và cài đặt các dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn dự án
COPY . /app

# Port mà Gunicorn sẽ chạy (mặc định 8000)
EXPOSE 8000

# # Lệnh mặc định sẽ được ghi đè bởi docker-compose.yml
# CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
