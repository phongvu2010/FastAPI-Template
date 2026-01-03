import aiofiles
import hashlib
import os
import uuid
import time
from abc import ABC, abstractmethod # Thêm thư viện cho Abstract Base Class
from datetime import datetime, timedelta
from fastapi import UploadFile, HTTPException
from pydantic import BaseModel
from typing import Dict, Tuple, Optional
import jwt # Thư viện để tạo Token (Signed URL giả lập)

from ..core.config import settings


# Cấu hình thư mục lưu trữ (ví dụ, có thể đưa vào config.py)
# Thư mục này phải tồn tại
# UPLOAD_DIR = "uploads/"
UPLOAD_DIR = settings.LOCAL_STORAGE_DIR 

# Đảm bảo thư mục upload tồn tại
os.makedirs(UPLOAD_DIR, exist_ok=True)

# GIẢ ĐỊNH: Cấu hình Secret cho Signed URL (Nên dùng Secret Key trong config.py)
# SIGNED_URL_SECRET = "SIGNED_URL_SECRET_KEY_CUC_BAO_MAT"
SIGNED_URL_SECRET = settings.SIGNED_URL_SECRET.get_secret_value()
# SIGNED_URL_ALGORITHM = "HS256"
SIGNED_URL_ALGORITHM = settings.ALGORITHM

class StorageResult(BaseModel):
    """
    Schema đơn giản để trả về kết quả sau khi lưu file.
    """
    file_path: str # Đường dẫn tương đối lưu trong DB
    file_hash: str # SHA-256 hash (Source 70)
    file_size: int

# =======================================================================
# 1. Lớp Trừu Tượng (Abstraction Layer)
# =======================================================================
class AbstractStorageService(ABC):
    @abstractmethod
    async def save_file_and_compute_hash(self, file: UploadFile, actor_id: uuid.UUID) -> StorageResult:
        raise NotImplementedError

class LocalStorageService(AbstractStorageService):
    """
    Triển khai Storage cho Local File System.
    """
    # Khởi tạo thư mục Local (chỉ nên chạy khi dùng LocalStorage)
    def __init__(self):
        os.makedirs(UPLOAD_DIR, exist_ok=True)

async def save_file_and_compute_hash(
    file: UploadFile,
    actor_id: uuid.UUID
) -> StorageResult:
    """
    Lưu file upload và tính toán SHA-256 đồng thời.
    (Source 161: Compute SHA256... streaming to avoid memory issues)
    """

    # Tạo một đường dẫn file an toàn và duy nhất
    # Dùng cấu trúc thư mục từ blueprint (Source 69)
    today = datetime.now()
    relative_dir = os.path.join(
        f"documents/{today.year}/{today.month:02d}/{today.day:02d}"
    )

    # Tạo thư mục con nếu chưa tồn tại
    full_dir_path = os.path.join(UPLOAD_DIR, relative_dir)
    os.makedirs(full_dir_path, exist_ok=True)

    # Tạo tên file duy nhất (giữ lại phần extension)
    file_extension = os.path.splitext(file.filename)[-1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"

    full_file_path = os.path.join(full_dir_path, unique_filename)
    relative_file_path = os.path.join(relative_dir, unique_filename)

    # Khởi tạo đối tượng hash SHA-256
    sha256_hash = hashlib.sha256()
    total_size = 0

    try:
        # Mở file để ghi (async)
        async with aiofiles.open(full_file_path, 'wb') as f:
            while True:
                # Đọc file theo từng chunk (streaming)
                chunk = await file.read(8192) # 8KB chunk
                if not chunk:
                    break

                # Cập nhật hash
                sha256_hash.update(chunk)
                # Ghi chunk vào file
                await f.write(chunk)
                total_size += len(chunk)

    except Exception as e:
        # Xử lý lỗi (ví dụ: ổ cứng đầy)
        # Cân nhắc xóa file nếu ghi lỗi
        if os.path.exists(full_file_path):
            os.remove(full_file_path)
        raise IOError(f"Lỗi khi lưu file: {e}")
    finally:
        # Đảm bảo file upload được đóng
        await file.close()

    # Lấy giá trị hash (dưới dạng hex)
    computed_hash = sha256_hash.hexdigest()

    return StorageResult(
        file_path=relative_file_path,
        file_hash=computed_hash,
        file_size=total_size
    )


# =======================================================================
# LOGIC SIGNED URL (TẢI XUỐNG AN TOÀN)
# =======================================================================

def create_signed_url(
    file_path: str,
    expires_in_seconds: int = 300
) -> str:
    """
    Tạo một Signed URL (dạng JWT Token) cho việc tải xuống.

    Trong thực tế với S3/G-Drive: Hàm này sẽ gọi SDK của S3/G-Drive để tạo URL.
    Với Local Server: Hàm này sẽ tạo JWT token để dùng làm khóa truy cập 1 lần.
    """

    # Thiết lập thời gian hết hạn
    expire = datetime.utcnow() + timedelta(seconds=expires_in_seconds)

    # Payload chứa thông tin file và thời gian hết hạn
    payload = {
        "sub": "download", # Subject: Download
        "file": file_path, # Đường dẫn file tương đối
        "exp": expire.timestamp(), # Thời gian hết hạn (timestamp)
        "iat": datetime.utcnow().timestamp() # Thời gian tạo
    }

    # Mã hóa thành JWT token
    token = jwt.encode(
        payload,
        SIGNED_URL_SECRET,
        algorithm=SIGNED_URL_ALGORITHM
    )

    # Trả về URL nội bộ mà API router sẽ xử lý
    # Ví dụ: GET /api/v1/download?token=...
    return f"/api/v1/download?token={token}"

def get_file_for_download(token: str) -> Tuple[str, str]:
    """
    Xác minh token và trả về đường dẫn file vật lý (Full Path) và Tên file.

    Returns: Tuple[full_file_path, original_filename]
    Raises: HTTPException nếu token không hợp lệ/hết hạn.
    """

    try:
        # Giải mã token
        payload = jwt.decode(
            token,
            SIGNED_URL_SECRET,
            algorithms=[SIGNED_URL_ALGORITHM]
        )

        file_path_relative = payload.get("file")
        if not file_path_relative:
            raise HTTPException(status_code=400, detail="Token thiếu thông tin file.")

        # 1. Xây dựng đường dẫn file vật lý
        full_file_path = os.path.join(UPLOAD_DIR, file_path_relative)

        # 2. Kiểm tra file có tồn tại không
        if not os.path.exists(full_file_path):
             raise HTTPException(status_code=404, detail="File không tồn tại trên server.")

        # 3. Trích xuất tên file (từ đường dẫn tương đối) để dùng làm tên tải xuống
        original_filename = os.path.basename(file_path_relative)

        return full_file_path, original_filename

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token tải xuống đã hết hạn.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token tải xuống không hợp lệ.")
    except Exception:
        raise HTTPException(status_code=500, detail="Lỗi xử lý token tải xuống.")
