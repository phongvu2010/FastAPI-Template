Bạn là 1 lập trình viên chuyên nghiệp về Python. Tôi đang có 1 dự án về quản lý hồ sơ & chữ ký số, các bước thực hiện như sau:
Bước 1: Người dùng sẽ nộp hồ sơ file pdf lên hệ thống.
- Nếu hồ sơ chưa được người kiểm tra `ký nháy` thì người dùng có thể upload lại hồ sơ. (Việc upload lại sẽ tạo các phiên bản để quản lý truy lục lại hồ sơ)
- Nếu hồ sơ được người kiểm tra `ký nháy` thì người dùng không thể upload lại hồ sơ.

Bước 2: Người kiểm tra sẽ xét duyệt.
- Nếu hồ sơ không đúng sẽ trả về cho người gửi upload lại tài liệu khác.
- Nếu hồ sơ được duyệt sẽ gửi lên cấp cao hơn để ký bằng chữ ký số bên ngoài (như USB token, phần mềm của Viettel-CA, VNPT-CA, FPT-CA...).

Bước 3: Sếp sẽ xem & ký chữ ký số.
- Nếu hồ sơ nội bộ có thể ký số như 1 chữ ký số nội bộ và hoàn tất quy trình.
- Nếu hồ sơ public bên ngoài, sẽ tải xuống & ký số bên ngoài, sau đó sẽ gửi lại hồ sơ đã có chữ ký số lên hệ thống hoàn tất quy trình.

Tất cả người có liên quan đến hồ sơ này đều có nhận thông báo quá trình xét duyệt & ký.

Dự án sẽ chạy dự án trên nền web, desktop hoặc mobile,... Các file pdf tạm thời sẽ được lưu trữ trên local server (sau này nếu có điều kiện sẽ upload lên các hệ thống khác như Google Drive, S3, ...), được tổ chức 1 cách hệ thống (có thể theo phòng ban, hoặc theo username người gửi lúc đầu) để dễ dàng truy suất. Về `ký nháy` hay `ký chính nội bộ`, cần có động tác nào đó để xác thực file không bị thay đổi, tránh trường hợp hệ thống bị `hack` thay file đã duyệt thì sẽ dẫn đến nguy hiểm.

Với vai trò là 1 admin quản trị, tôi không muốn quản lý user như `mật khẩu` user để không phải dính trách nhiệm trường hợp admin cố tình đổi mật khẩu để ký 1 văn bản nào đó, nên muốn sử dụng user Gmail như SSO để trường hợp quên mật khẩu thì sẽ dùng đơn vị Gmail thay đổi. Nhiệm vụ của admin chỉ cấp quyền vai trò của user thôi.

Ngoài ra, cần thêm bảng AuditLog: Ghi lại lịch sử không thể xóa (ai làm gì, khi nào, kể cả lý do từ chối, ...).











document-manager/
├── app/
│   ├── api/
│   │   ├── __init__.py          # PACKAGE
│   │   ├── endpoints/           # Định nghĩa các endpoint API
│   │   │   ├── __init__.py      # PACKAGE
│   │   │   ├── documents.py     # API routes cho Document
│   │   │   └── users.py         # API routes cho User (đăng nhập, đăng ký)
│   │   └── dependencies.py      # Đã chuyển vào api/
│   ├── models/                  # Mô hình DB (Document, DocumentVersion, AuditLog)
│   │   ├── __init__.py          # PACKAGE (dùng để import Base Class)
│   │   └── documents.py         # SQLAlchemy Model cho Document, DocumentVersion, AuditLog
│   │   └── users.py             # SQLAlchemy Model cho User
│   ├── cruds/                   # Thao tác DB (Create, Read, Update, Delete)
│   │   ├── __init__.py
│   │   └── documents.py         # CRUD logic cho Document
│   │   └── users.py             # CRUD logic cho User
│   ├── schemas/                 # Mô hình dữ liệu Pydantic (input/output API)
│   │   ├── __init__.py
│   │   └── documents.py         # Pydantic Schemas cho Document
│   │   └── users.py             # Pydantic Schemas cho User
│   ├── utils/
│   │   ├── __init__.py          # PACKAGE
│   │   ├── file_handler.py      # Logic lưu file local/đường dẫn tương đối
│   │   └── signer.py            # Logic ký nháy và xác thực chữ ký (pyhanko)
│   ├── configs/
│   │   ├── __init__.py          # PACKAGE
│   │   ├── settings.py          # Cấu hình Pydantic
│   │   └── database.py          # Kết nối DB & get_db()
│   ├── __init__.py              # PACKAGE GỐC
│   ├── main.py                  # Khởi tạo FastAPI
│   └── celery_app.py            # Cấu hình Celery và các task nền
│   └── tasks.py                 # Tác vụ nền Celery
├── Dockerfile                   # Hướng dẫn xây dựng image Python
├── .gitignore
├── requirements.txt             # Danh sách các thư viện Python
├── docker-compose.yml           # Định nghĩa các service Docker
└── .env                         # Biến môi trường