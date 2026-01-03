# Sơ đồ cấu trúc dự án:
```
SignHub/
├── alembic/                    # Quản lý migrations (Rất quan trọng với PostgreSQL)
├── app/
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/      # Thay vì để routers ngay trong v1, hãy gom vào endpoints
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py     # (Cũ: router_auth.py)
│   │   │   │   ├── users.py    # (Cũ: router_users.py)
│   │   │   │   └── web.py      # (Cũ: router_frontend.py) - Tên 'web' hoặc 'views' hợp lý hơn cho HTMX
│   │   │   ├── __init__.py
│   │   │   └── api.py          # Tập hợp tất cả router include tại đây
│   │   ├── __init__.py
│   │   └── deps.py             # Dependencies (Get DB session, Get Current User)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Cấu hình Celery instance
│   │   ├── config.py           # (Cũ: settings.py) - Chuẩn chung thường dùng config
│   │   └── security.py         # (Cũ: auth.py) - Chứa hàm hash pass, tạo JWT token
│   ├── crud/                   # TÁCH BIỆT: Chỉ chứa logic tương tác DB (Create, Read, Update, Delete)
│   │   ├── __init__.py
│   │   ├── base.py             # Class CRUDGeneric để tái sử dụng
│   │   └── crud_user.py        # Các query cụ thể cho User
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py             # Import tất cả models vào đây để Alembic nhận diện
│   │   └── session.py          # Engine và SessionLocal
│   ├── models/                 # TÁCH BIỆT: Mỗi bảng 1 file hoặc gom nhóm
│   │   ├── __init__.py
│   │   ├── base_class.py       # Base model
│   │   ├── user.py
│   │   └── role.py
│   ├── schemas/                # TÁCH BIỆT: Pydantic models
│   │   ├── __init__.py
│   │   ├── common.py           # Các schema dùng chung (Msg, Pagination)
│   │   ├── user.py             # UserCreate, UserUpdate, UserResponse
│   │   └── token.py
│   ├── services/               # Logic nghiệp vụ phức tạp (Gửi mail, Xử lý ảnh, PDF...)
│   │   ├── __init__.py
│   │   └── email.py            # Ví dụ: Gửi email chào mừng qua Celery
│   ├── static/                 # CSS, JS, Images (HTMX, Tailwind...)
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── tasks/                  # Celery Tasks cụ thể
│   │   ├── __init__.py
│   │   └── background_tasks.py
│   ├── templates/              # Jinja2 Templates
│   │   ├── components/         # Các đoạn HTML nhỏ cho HTMX (Partial views)
│   │   │   ├── navbar.html
│   │   │   └── user_row.html
│   │   ├── layouts/            # Base layout (head, body tags)
│   │   │   └── base.html
│   │   ├── admin/
│   │   └── auth/
│   │       └── login.html
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   └── worker.py               # Entry point để chạy Celery Worker
├── alembic.ini                 # Config của Alembic
├── .env
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```



```
SignHub/
├── app/
│   ├── api/                        # Quản lý các endpoints
│   │   ├── v1/                     # Định phiên bản API
│   │   │   ├── __init__.py
│   │   │   ├── router_auth.py      # Endpoints cho /auth
│   │   │   ├── router_frontend.py  # Endpoints cho /frontend
│   │   │   └── router_users.py     # Endpoints cho /users
│   │   ├── __init__.py
│   │   └── deps.py                 # Chứa dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Logic xử lý Google SSO (ví dụ: xác thực token)
│   │   └── settings.py             # Quản lý settings, Google Client ID/Secret
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Cấu hình kết nối DB, Base (DeclarativeBase)
│   │   ├── models.py               # Models: User, Role
│   │   └── schemas.py              # Pydantic schemas (UserRead, RoleCreate...)
│   ├── services/                   # Logic nghiệp vụ (business logic)
│   │   ├── __init__.py
│   │   └── user_crud.py            # Logic: create_user, assign_role...
│   ├── static/
│   ├── templates/
│   │   ├── admin_panel.html
│   │   ├── dashboard.html
│   │   └── login.html
│   ├── __init__.py
│   ├── Dockerfile
│   ├── main.py                     # Ứng dụng FastAPI chính
│   └── requirements.txt
├── .dockerignore
├── .env
├── .gitignore
└── docker-compose.yml
```


```
SECUREDOCFLOW
├── app/
│   ├── api/                    # Định nghĩa API Endpoints (FastAPI Routers)
│   │   ├── v1/                 # Version 1 của API
│   │   │   ├── __init__.py
│   │   │   ├── admin.py        # Endpoints cho admin
│   │   │   ├── documents.py    # Endpoints cho /documents 
│   │   │   ├── router.py       # Gộp tất cả các router con
│   │   │   └── users.py        # Endpoints cho /users, /auth
│   │   └── __init__.py
│   ├── core/                   # Cấu hình, bảo mật, và logic cốt lõi
│   │   ├── __init__.py
│   │   ├── config.py           # Pydantic Settings (quản lý env variables)
│   │   ├── security.py         # Logic auth, RBAC dependencies, Google SSO 
│   │   └── signing.py          # Logic ký số nội bộ (dùng crypto) 
│   ├── db/                     # Database
│   │   ├── __init__.py
│   │   ├── base.py             # Khởi tạo SQLAlchemy Base, session
│   │   ├── models.py           # SQLAlchemy models (Document, User, etc.) 
│   │   └── schemas.py          # Pydantic schemas (DocumentCreate, UserRead, etc.)
│   ├── services/               # Nơi chứa logic nghiệp vụ
│   │   ├── __init__.py
│   │   ├── audit_service.py    # Hàm helper create_audit 
│   │   ├── document_service.py # Logic (approve, reject, upload...)
│   │   └── storage_service.py  # Lớp trừu tượng (Local/G-Drive)
│   ├── worker/                 # Celery worker
│   │   ├── __init__.py
│   │   ├── celery_app.py       # Khởi tạo Celery
│   │   └── tasks.py            # Các tasks (verify hash, notifications) 
│   ├── __init__.py
│   └── main.py                 # Khởi tạo FastAPI app, middleware
├── alembic/                    # Thư mục Alembic (migrations)
│   ├── versions
│   └── ...
├── alembic.ini                 # Cấu hình Alembic
├── docker-compose.yml          # (web, db, redis, celery)
├── Dockerfile                  # Cho FastAPI app
├── .env                        # Biến môi trường 
└── requirements.txt
```
