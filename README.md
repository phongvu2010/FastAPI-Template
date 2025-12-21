# 🛡️ SecureDocFlow - Document Management & Digital Signature

****SecureDocFlow**** là một hệ thống quản lý tài liệu và ký số nội bộ, tập trung vào tính bảo mật, toàn vẹn dữ liệu (Data Integrity) và quy trình phê duyệt chặt chẽ (Check-and-Balance). Hệ thống sử dụng công nghệ bất đồng bộ (Async) để đảm bảo hiệu suất cao và tích hợp Google SSO cho bảo mật doanh nghiệp.

## 🚀 Tính năng nổi bật (Core Features)

* **Xác thực tập trung (Google SSO):** Loại bỏ việc quản lý mật khẩu thủ công, tích hợp chặt chẽ với Google Workspace.

* **Phân quyền dựa trên vai trò (RBAC):** Quản lý linh hoạt qua 4 nhóm quyền: `SENDER`, `CHECKER`, `MANAGER`, và `ADMIN`.

* **Cơ chế bảo mật đa lớp:** Sử dụng **JWT (JSON Web Token)** lưu trong **HttpOnly Cookie**.

    * Bảo vệ chống tấn công **CSRF** (Cross-Site Request Forgery).

    * Hạn chế tên miền đăng nhập (Domain Restriction).

* **Giao diện hiện đại (Modern Monolith):** Kết hợp giữa FastAPI Jinja2 Templates (SSR) và xử lý tương tác qua Fetch API (CSRF-aware).

* **Audit Trail:** Ghi lại dấu vết mọi hành động nhạy cảm trên hệ thống (Sắp triển khai).

## 🛠️ Công nghệ sử dụng (Technical Stack)

* **Backend:** Python 3.12, FastAPI (Async).

* **Database:** PostgreSQL 17 với SQLAlchemy 2.0 (AsyncIO) & SQLModel.

* **Frontend:** Tailwind CSS, Jinja2, JavaScript (Vanilla ES6+).

* **Migration:** Alembic.

* **Containerization:** Docker & Docker Compose.

## 📁 Cấu trúc thư mục (Project Structure)

```
app/
├── api/                # Các Router xử lý JSON API
│   ├── v1/             # Phiên bản API chính
│   └── deps.py         # Dependencies (Auth, Role, DB session)
├── core/               # Cấu hình lõi (Security, Config, DB Engine)
├── crud/               # Logic thao tác trực tiếp với Database
├── models/             # Định nghĩa Schema và DB Models (SQLModel)
├── services/           # Logic nghiệp vụ (Auth, Sign, File processing)
├── static/             # Assets (CSS, JS, Images)
├── templates/          # Giao diện Jinja2 (HTML)
└── web/                # Router render giao diện (Views)
```

## ⚙️ Quy trình triển khai (Setup & Installation)

#### 1. Cấu hình biến môi trường

Tạo file `.env` tại thư mục gốc và cấu hình các thông số sau:
```
# Google OAuth
GOOGLE_CLIENT_ID=your_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_secret
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/auth/callback

# Security
JWT_SECRET_KEY=your_secure_jwt_key
CSRF_SECRET_KEY=your_secure_csrf_key
INITIAL_ADMIN_EMAIL=admin@yourcompany.com
ALLOWED_EMAIL_DOMAINS=yourcompany.com

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password
POSTGRES_DB=securedoc_db
POSTGRES_SERVER=db
```

#### 2. Khởi động với Docker
``` Bash
docker-compose up -d --build
```

#### 3. Migrations & Initial Data
Hệ thống sẽ tự động khởi tạo các vai trò mặc định (`SENDER`, `CHECKER`, `MANAGER`, `ADMIN`) thông qua script `initial_data.py`.

## 🔄 Luồng hoạt động chính (User Workflow)

1. **Đăng nhập:** Người dùng đăng nhập qua Google SSO.

2. **Kích hoạt:** Admin nhận thông báo, kiểm tra và chuyển trạng thái User sang `Active`, đồng thời gán Role phù hợp.

3. **Hồ sơ:** User có thể cập nhật thông tin Phòng ban và Email liên hệ tại trang Profile cá nhân.

4. **Luồng ký (Tiếp theo):**

    * `SENDER` upload file và tính SHA-256 hash.

    * `CHECKER` phê duyệt / từ chối.

    * `MANAGER` thực hiện ký số pháp lý.

## 🔒 Ghi chú bảo mật

* Toàn bộ mã nguồn sử dụng cơ chế **Streaming Hash** để kiểm tra tính toàn vẹn của file mà không làm tràn RAM.

* Khóa ký (Private Key) được khuyến nghị lưu trữ trong các dịch vụ quản lý khóa (KMS) ở môi trường Production.

**SecureDocFlow** - ***Building Trust through Technology.***