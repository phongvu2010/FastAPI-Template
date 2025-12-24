# --- Giai đoạn 1: Builder (Cài đặt Dependencies) ---
# Sử dụng base image Python 3.12-slim làm môi trường build
FROM python:3.12-slim AS builder

# Thiết lập các biến môi trường cho Python
# PYTHONDONTWRITEBYTECODE=1: Ngăn Python tạo tệp .pyc
# PYTHONUNBUFFERED=1: Đảm bảo log được in ra ngay lập tức
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/src

# Thiết lập thư mục làm việc bên trong container
WORKDIR /src

# Sao chép tệp requirements.txt
COPY ./requirements.txt .

# Cài đặt các thư viện Python
# --no-cache-dir: Giảm kích thước image cuối cùng
RUN pip install --no-cache-dir -r requirements.txt

# # Install uv
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
# COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# # Place executables in the environment at the front of the path
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
# ENV PATH="/app/.venv/bin:$PATH"

# # Compile bytecode
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#compiling-bytecode
# ENV UV_COMPILE_BYTECODE=1

# # uv Cache
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#caching
# ENV UV_LINK_MODE=copy

# # Install dependencies
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
# RUN --mount=type=cache,target=/root/.cache/uv \
#     --mount=type=bind,source=uv.lock,target=uv.lock \
#     --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
#     uv sync --frozen --no-install-project

# # Sync the project
# # Ref: https://docs.astral.sh/uv/guides/integration/docker/#intermediate-layers
# RUN --mount=type=cache,target=/root/.cache/uv \
#     uv sync


# --- Giai đoạn 2: Runtime (Image cuối cùng) ---
# Sử dụng lại base image Python 3.12-slim cho môi trường chạy
FROM python:3.12-slim AS runtime

# --- Cấu hình Non-root User (Bảo mật) ---
# 1. Tạo một nhóm (group) và người dùng (user) không có quyền root
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 2. Thiết lập thư mục
WORKDIR /src
# RUN chown -R appuser:appuser /src

# --- Sao chép các thành phần cần thiết ---
# 3. Sao chép các thư viện đã được cài đặt từ giai đoạn 'builder' sang giai đoạn 'runtime' hiện tại
# Điều này giúp image runtime không chứa các công cụ build/cache.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages

# 4. Sao chép các tệp thực thi (uvicorn) từ /usr/local/bin/ của builder
COPY --from=builder /usr/local/bin/ /usr/local/bin/

# 5. Sao chép toàn bộ mã nguồn của dự án (trong ngữ cảnh build) vào thư mục /src trong container
# COPY ./pyproject.toml ./uv.lock ./alembic.ini /src
COPY --chown=appuser:appuser ./alembic.ini /src
COPY --chown=appuser:appuser ./app /src/app
COPY --chown=appuser:appuser ./scripts /src/scripts
COPY --chown=appuser:appuser ./static /src/static
COPY --chown=appuser:appuser ./templates /src/templates

# 6. Chuyển sang non-root user để chạy ứng dụng (BEST PRACTICE)
USER appuser

# Mở cổng 8000 của container để bên ngoài có thể truy cập
EXPOSE 8000

# Lệnh CMD mặc định để khởi chạy ứng dụng
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
# CMD ["fastapi", "run", "app/main.py", "--workers", "4"]
