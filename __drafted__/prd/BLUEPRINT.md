# HỆ THỐNG QUẢN LÝ HỒ SƠ & CHỮ KÝ SỐ

## I. Tổng quan Kỹ thuật (Technical Stack)

Hệ thống được chuyển đổi sang kiến trúc hiện đại, hiệu năng cao, tập trung vào tính bất đồng bộ (Asynchronous).

* **Language:** Python 3.12+
* **Framework:** FastAPI (High performance, Async).
* **Database:** PostgreSQL 16.
* **ORM:** SQLAlchemy 2.0 (AsyncIO) + Alembic (Migration).
* **Validation:** Pydantic v2.
* **Template Engine:** Jinja2 (Server-side rendering cho giao diện Admin/Dashboard).
* **Containerization:** Docker & Docker Compose (Multi-stage build, Non-root user).


## II. Kiến trúc Bảo mật & Xác thực (Security & Auth)

### 1. Cơ chế Xác thực (Authentication)

Hệ thống sử dụng luồng OAuth2 tùy chỉnh kết hợp JWT an toàn:

* **Google SSO (OIDC):**
  * Sử dụng `google-auth` và `httpx` để trao đổi mã xác thực.
  * Không lưu password người dùng.
  * Định danh duy nhất dựa trên `google_sub` (Subject ID).

* **Session Management:**
  * **JWT (JSON Web Token):** Chứa `sub` (Google ID) và `exp` (Expiration).
  * **Storage:** Token được lưu trong **HttpOnly Cookie** (`access_token`).
  * **Security:** Ngăn chặn Javascript truy cập token (chống XSS), cấu hình `SameSite=Lax` và `Secure` (trên Prod).

* **Auto-Provisioning & Admin Bootstrapping:**
  * User mới đăng nhập lần đầu sẽ tự động được tạo account với role mặc định `SENDER`.
  * **Cơ chế "First Admin":** Hệ thống kiểm tra email đăng nhập. Nếu khớp với biến môi trường `INITIAL_ADMIN_EMAIL`, user sẽ lập tức được thăng cấp lên `ADMIN`.

### 2. Phân quyền (RBAC)

Sử dụng mô hình Role-Based Access Control với bảng trung gian `user_role_association` (Many-to-Many).

* **Roles:** `SENDER`, `CHECKER`, `MANAGER`, `ADMIN` (Enum).
* **Enforcement:** Sử dụng Dependency `require_role([...])` tại các API Endpoint.


## III. Thiết kế Cơ sở dữ liệu (Database Schema)

Sử dụng SQLAlchemy Async Models. Các bảng hiện tại và dự kiến:

### 1. Core Models (Đã triển khai)

* **User (`user`):**
    * `id`: Integer (PK).
    * `google_sub`: String (Unique Index).
    * `email`: String (Unique).
    * `is_active`: Boolean.
    * `roles`: Relationship (Many-to-Many).

* **Role (`role`):**
    * `id`: Integer (PK).
    * `name`: Enum (`Admin`, `Manager`,...).
    * `description`: String.

### 2. Document Models (Quy hoạch cho Sprint tiếp theo)

Dựa trên logic nghiệp vụ cũ nhưng chuyển sang SQLAlchemy:

* **Document (`document`):**
    * `creator_id`: FK tới User.
    * `status`: Enum (`PENDING`, `APPROVED_SIGNING`, `COMPLETED`,...).
    * `current_version_id`: FK tới DocumentVersion.

* **DocumentVersion (`document_version`):**
    * `document_id`: FK.
    * `file_path`: String (Path trên Disk/MinIO).
    * `file_hash`: String (SHA-256 Immutable).
    * `version_num`: Integer.

* **AuditLog (`audit_log`):**
    * `actor_id`: FK User.
    * `action`: Enum (`UPLOAD`, `APPROVE`, `SIGN`,...).
    * `timestamp`: DateTime (UTC).

Lưu ý: Cần thiết lập Database Trigger (PostgreSQL function) để ngăn chặn lệnh DELETE hoặc UPDATE trên bảng này.


## IV. Cấu trúc Dự án (Project Structure)

Tuân thủ Clean Architecture/Layered Architecture:

```
SecureDocFlow/
├── app/
│   ├── api/                        # Quản lý các endpoints
│   │   ├── v1/                     # Định phiên bản API
│   │   │   ├── __init__.py
│   │   │   ├── router_auth.py      # Endpoints cho /auth
│   │   │   ├── router_documents.py # Endpoints cho /documents 
│   │   │   ├── router_frontend.py  # Endpoints cho /frontend
│   │   │   └── router_users.py     # Endpoints cho /users
│   │   ├── __init__.py
│   │   └── deps.py                 # Chứa dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── auth.py                 # Logic xử lý Google SSO (ví dụ: xác thực token)
│   │   ├── settings.py             # Quản lý settings, Google Client ID/Secret
│   │   └── signing.py              # Logic ký số nội bộ (dùng crypto) 
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py                 # Cấu hình kết nối DB, Base (DeclarativeBase)
│   │   ├── models.py               # Models: User, Role
│   │   └── schemas.py              # Pydantic schemas (UserRead, RoleCreate...)
│   ├── services/                   # Logic nghiệp vụ (business logic)
│   │   ├── __init__.py
│   │   ├── audit_crud.py           # Hàm helper create_audit 
│   │   ├── document_crud.py        # Logic (approve, reject, upload...)
│   │   └── storage_crud.py         # Lớp trừu tượng (Local/G-Drive)
│   │   └── user_crud.py            # Logic: create_user, assign_role...
│   ├── static/
│   ├── templates/
│   │   ├── admin_panel.html
│   │   ├── dashboard.html
│   │   └── login.html
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py           # Khởi tạo Celery
│   │   └── tasks.py                # Các tasks (verify hash, notifications) 
│   ├── __init__.py
│   ├── Dockerfile
│   ├── main.py                     # Ứng dụng FastAPI chính
│   └── requirements.txt
├── .dockerignore
├── .env
├── .gitignore
└── docker-compose.yml
```


## V. Quy trình Nghiệp vụ Chính (Workflows)

### 1. Luồng Đăng nhập & Khởi tạo
* User truy cập `/auth/login` -> Redirect Google.
* Google trả về Code -> Backend trao đổi lấy ID Token & Access Token.
* Backend xác thực ID Token -> Lấy email/sub.
* Logic Backend:
  * User tồn tại ? -> Update info -> Tạo Session.
  * User mới ? -> Tạo User -> Check `INITIAL_ADMIN_EMAIL` -> Gán Role (Admin/Sender) -> Tạo Session.
* Backend set `HttpOnly Cookie` và redirect về `/app`.

### 2. Luồng Quản lý User (Admin)
* Admin truy cập `/admin` -> Gọi API `/users/`.
* Admin thực hiện `POST /users/{id}/roles` hoặc `PATCH /users/{id}/status`.
* Frontend (JS) gửi request (Cookie tự động đính kèm).
* Backend kiểm tra `require_role([ADMIN])` -> Thực thi Logic -> Trả về JSON.
* Frontend cập nhật UI (DOM manipulation) không cần reload.

### 3. Luồng Xử lý Tài liệu (Planned)
* **Upload (Sender):** `POST /documents/` (Multipart) -> Lưu file -> Tính Hash SHA256 -> Lưu DB -> Ghi Audit Log.
* **Approve (Checker):** `POST /documents/{id}/approve` -> Đổi status -> Ghi Audit Log.
* **Sign (Manager):**
  * **Internal:** Server dùng Private Key (được load an toàn từ ENV/KMS) ký lên Hash của file -> Lưu chữ ký vào bảng `Signature`.
  * **External:** Manager download file -> Ký bằng USB Token -> Upload file đã ký -> Server verify hash & signature -> Lưu.


## VI. Kế hoạch Triển khai (Roadmap)

### Giai đoạn 1: Core Foundation (Đã hoàn thành)
* [x] Thiết lập Docker/PostgreSQL Async.
* [x] Google SSO Integration.
* [x] User/Role Management (DB Models & API).
* [x] Admin Dashboard cơ bản (Jinja2).
* [x] Bảo mật JWT qua Cookie.

### Giai đoạn 2: Document Management (Tiếp theo)
* [x] Tạo Model Document, DocumentVersion.
* [x] API Upload file (lưu trữ Local hoặc MinIO).
* [x] Logic tính SHA-256 hash (Streaming để tiết kiệm RAM).
* [ ] API Download file (Secure Link).

### Giai đoạn 3: Workflow & Audit
* [x] Logic Approve/Reject cho Checker.
* [ ] Tạo bảng AuditLog & Trigger chống xóa trong PostgreSQL.
* [x] Giao diện Dashboard hiển thị danh sách hồ sơ theo trạng thái.

### Giai đoạn 4: Digital Signature
* [x] Tích hợp thư viện cryptography hoặc pyca/cryptography.
* [x] Logic ký số RSA/PSS nội bộ.
* [ ] API Verify chữ ký.



- [x] Gom 2 func upload & reup thành một
- [ ] Viết hàm kiểm tra giả mạo tài liệu

- [ ] Triển khai lưu trữ Local hoặc Cloud
- [ ] Triển khai nhúng chữ ký vào tài liệu





Tư vấn Lưu trữ Nâng cao (Cloud): Đối với dự án sản phẩm, tôi khuyến nghị chuyển sang MinIO hoặc S3/GCS. Thay vì lưu file_path cục bộ, bạn lưu Object Key (chính là đường dẫn cấu trúc trên) và sử dụng Signed URL để cấp quyền truy cập tạm thời cho người dùng khi họ cần download. Điều này giúp tăng tính sẵn sàng, độ bền, và bảo mật (không cần phơi bày file trực tiếp).
Để tôi có thể tư vấn kiến trúc lưu trữ (Local vs. Cloud/MinIO) và Celery/Redis tối ưu, bạn có thể cho biết ước tính về tần suất giao dịch (transaction frequency) hàng ngày (số lượng hồ sơ upload/ký duyệt) và dung lượng file trung bình là bao nhiêu không?
Ví dụ: 100 giao dịch/ngày với file 5MB, hay 5000 giao dịch/ngày với file 50MB.



Logic ngăn chặn upload file giống hệt đã được đề cập là kiểm tra file_hash. Bạn cần triển khai cơ chế này trong router_documents.py, cụ thể là trong hàm handle_document_upload.




pyHanko: Thư viện mạnh nhất hiện nay để xử lý PDF Signature trong Python (Verify chữ ký, Embed chữ ký, Lấy thông tin Signer).


Bảng Signature:
Thêm cột signer_name: Lưu tên người ký (lấy từ Certificate trong file PDF) -> Hiển thị: "Đã ký bởi: NGUYEN VAN A".
Thêm cột signing_time: Thời gian ký (lấy từ timestamp trong chữ ký, khác với thời gian upload).

Bảng Document:
Thêm cột is_locked (Boolean): Để tách biệt rõ ràng logic khóa, thay vì chỉ phụ thuộc vào Enum status


UI Feedback: Tại endpoint approve_document_htmx, ngoài việc trả về thông báo thành công, hãy trả về cả dòng trạng thái mới của hồ sơ (sử dụng hx-swap="outerHTML") để giao diện cập nhật tức thì mà không cần reload trang.
