import os
from pathlib import Path

# Cấu hình gốc
BASE_STORAGE_PATH = Path("/var/data/hoso/") # Đường dẫn tuyệt đối trên server

def get_document_folder(dept_code: str, doc_code: str) -> Path:
    """Xây dựng đường dẫn đến thư mục chứa tất cả phiên bản của một hồ sơ."""
    # Ví dụ: /var/data/hoso/KINH_DOANH/HSKD_0001/
    return BASE_STORAGE_PATH / dept_code / doc_code

def save_new_version(dept_code: str, doc_code: str, file_data: bytes, version_name: str) -> str:
    """Lưu file mới và trả về đường dẫn tương đối."""
    
    # 1. Xác định đường dẫn thư mục và đảm bảo nó tồn tại
    doc_folder = get_document_folder(dept_code, doc_code)
    doc_folder.mkdir(parents=True, exist_ok=True) # Tạo thư mục nếu chưa có
    
    # 2. Xây dựng tên file (Đảm bảo tên file là duy nhất, ví dụ: V{version_number}_name.pdf)
    file_name = f"{version_name}.pdf"
    
    # 3. Đường dẫn tuyệt đối để ghi file
    full_path = doc_folder / file_name
    
    # 4. Ghi file vào ổ đĩa
    with open(full_path, "wb") as f:
        f.write(file_data)
        
    # 5. Trả về đường dẫn tương đối để lưu vào DB
    # Ví dụ: KINH_DOANH/HSKD_0001/V2_fixed_by_uploader.pdf
    relative_path = full_path.relative_to(BASE_STORAGE_PATH)
    return str(relative_path)

def get_full_path(relative_path: str) -> Path:
    """Chuyển đường dẫn tương đối từ DB thành đường dẫn tuyệt đối để đọc file."""
    return BASE_STORAGE_PATH / relative_path




# import hashlib

# from pathlib import Path
# from typing import Tuple

# from ..configs.settings import settings

# # Đường dẫn gốc bây giờ được lấy trực tiếp từ Pydantic
# BASE_STORAGE_PATH: Path = settings.BASE_STORAGE_PATH

# def get_document_folder(dept_code: str, doc_code: str) -> Path:
#     """
#     Xây dựng và trả về đường dẫn tuyệt đối đến thư mục chứa file của một hồ sơ.
#     Ví dụ: /code/app_storage/KINH_DOANH/HSKD_0001
#     """
#     return BASE_STORAGE_PATH / dept_code / doc_code

# def save_file(
#     file_data: bytes,
#     dept_code: str,
#     doc_code: str,
#     version_filename: str
# ) -> Tuple[str, str]:
#     """
#     Lưu file vào local server và trả về (relative_path, file_hash).

#     Args:
#         file_data (bytes): Dữ liệu file (nội dung).
#         dept_code (str): Mã phòng ban (ví dụ: "KINH_DOANH").
#         doc_code (str): Mã hồ sơ (ví dụ: "HSKD_0001").
#         version_filename (str): Tên file của phiên bản (ví dụ: "V1_original.pdf").

#     Returns:
#         Tuple[str, str]: (relative_path, file_hash_sha256)
#     """
#     # 1. Tính toán Hash (SHA-256) của file
#     # (Quan trọng: Phải làm điều này trước khi file được ghi)
#     file_hash = hashlib.sha256(file_data).hexdigest()

#     # 2. Xây dựng đường dẫn
#     doc_folder = get_document_folder(dept_code, doc_code)
#     full_path = doc_folder / version_filename

#     # 3. Tạo thư mục nếu nó chưa tồn tại
#     # (parents=True: tạo các thư mục cha, exist_ok=True: không báo lỗi nếu đã tồn tại)
#     doc_folder.mkdir(parents=True, exist_ok=True)

#     # 4. Ghi file (sử dụng "wb" - write binary)
#     try:
#         with open(full_path, "wb") as f:
#             f.write(file_data)
#     except IOError as e:
#         # (Xử lý lỗi ghi file ở đây, ví dụ: log lỗi)
#         print(f"Lỗi khi ghi file: {e}")
#         raise

#     # 5. Tính toán đường dẫn tương đối để lưu vào DB
#     # Ví dụ: "KINH_DOANH/HSKD_0001/V1_original.pdf"
#     relative_path = str(full_path.relative_to(BASE_STORAGE_PATH))

#     return (relative_path, file_hash)

# def get_full_path(relative_path: str) -> Path:
#     """
#     Chuyển đổi đường dẫn tương đối (lưu trong DB) thành đường dẫn tuyệt đối.
#     """
#     return BASE_STORAGE_PATH / relative_path

# def read_file(relative_path: str) -> bytes:
#     """
#     Đọc nội dung (bytes) của một file từ đường dẫn tương đối.
#     (Hữu ích cho việc ký nháy hoặc xác thực).
#     """
#     full_path = get_full_path(relative_path)

#     if not full_path.exists():
#         raise FileNotFoundError(f"Không tìm thấy file tại: {full_path}")

#     with open(full_path, "rb") as f:
#         return f.read()

# def delete_file(relative_path: str) -> bool:
#     """
#     Xóa một file vật lý dựa trên đường dẫn tương đối.
#     (Hữu ích khi cần rollback giao dịch).
#     """
#     full_path = get_full_path(relative_path)
#     try:
#         full_path.unlink(missing_ok=True) # missing_ok=True: không báo lỗi nếu file không tồn tại
#         return True
#     except OSError as e:
#         # (Log lỗi)
#         print(f"Lỗi khi xóa file: {e}")
#         return False
