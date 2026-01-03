import hashlib
import io
import os
import uuid
from typing import Optional, Dict, Any

# Thư viện cho Crypto và Ký số Nội bộ
# Cần cài đặt: pip install cryptography
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import utils as crypto_utils
from cryptography.hazmat.backends import default_backend

# Import models và schemas
from ..db import schemas
from ..db import models


# GIẢ ĐỊNH: Import cấu hình Key
# Trong thực tế, Private Key nên được tải từ KMS/HSM hoặc file bảo mật cao
class SigningSettings:
    # Path tới Private Key (cho Ký Nội bộ RSA/PSS)
    INTERNAL_PRIVATE_KEY_PATH = "keys/internal_signing_private.pem"
    # Mật khẩu Private Key (nếu có)
    PRIVATE_KEY_PASSWORD = b"super-secret-password"
    # API key cho Viettel-CA/VNPT-CA (nếu dùng External)
    EXTERNAL_API_URL = "https://api.viettel-ca.vn/sign"

signing_settings = SigningSettings()

# =======================================================================
# 1. Logic Ký số Nội bộ (Internal RSA/PSS)
# =======================================================================

class InternalSigner:
    """
    Xử lý Ký số Nội bộ (Internal) bằng RSA/PSS. (Source 2)
    Giả định Private Key đã được bảo mật.
    """

    def __init__(self):
        # Tải Private Key khi khởi tạo
        try:
            with open(signing_settings.INTERNAL_PRIVATE_KEY_PATH, "rb") as key_file:
                self.private_key = serialization.load_pem_private_key(
                    key_file.read(),
                    password=signing_settings.PRIVATE_KEY_PASSWORD,
                    backend=default_backend()
                )
        except FileNotFoundError:
            # Ghi Log: Cần tạo key cho môi trường DEV
            print(f"LƯU Ý: Không tìm thấy key tại {signing_settings.INTERNAL_PRIVATE_KEY_PATH}. Cần tạo key.")
            self.private_key = None # Giữ None nếu key không tải được

    def sign_hash(self, data_hash: str) -> bytes:
        """Ký trên SHA-256 Hash của file (Không ký trực tiếp lên file)"""
        if not self.private_key:
            raise Exception("Internal Private Key chưa được tải hoặc không tồn tại.")

        # Dữ liệu cần ký là hash của file (dạng bytes)
        hash_bytes = bytes.fromhex(data_hash)

        # Thiết lập Padding PSS (Probabilistic Signature Scheme)
        signer = self.private_key.signer(
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256() # Hash mà chúng ta đang ký (SHA256)
        )

        signer.update(hash_bytes)
        signature = signer.finalize()

        return signature

    def get_public_key(self) -> str:
        """Trích xuất Public Key để lưu vào DB và phục vụ cho việc Verify"""
        if not self.private_key:
            return "" # Trả về rỗng nếu key không tải được

        public_key = self.private_key.public_key()
        pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        return pem.decode('utf-8')


# =======================================================================
# 2. Logic Ký số Bên ngoài (External CA)
# =======================================================================

class ExternalCAService:
    """
    Service giả lập cho việc tích hợp với Viettel-CA, VNPT-CA, FPT-CA. (Source 180-186)
    Việc này thường yêu cầu gọi API HTTP, không xử lý crypto trực tiếp.
    """

    # Hàm này sẽ được gọi từ document_service
    async def request_external_sign(
        self,
        document_version: models.DocumentVersion,
        signer: models.User
    ) -> Dict[str, Any]:
        """
        Gửi yêu cầu Ký số tới dịch vụ CA bên ngoài (API Call).
        Đây là hàm placeholder, cần triển khai HTTP request thực tế.
        """
        # GIẢ LẬP: Thực hiện HTTP POST request tới External API (Viettel-CA)
        # Yêu cầu gửi file, hash, hoặc link file (Signed URL)

        # Dữ liệu gửi đi:
        request_payload = {
            "document_hash": document_version.file_hash,
            "signer_email": signer.email,
            "callback_url": "YOUR_SYSTEM_API_URL/external/callback"
        }

        # Trong thực tế, bạn sẽ dùng 'import httpx' hoặc 'requests'
        # response = await httpx.post(signing_settings.EXTERNAL_API_URL, json=request_payload)

        # Trả về metadata của yêu cầu (ví dụ: request_id)
        return {
            "status": "REQUESTED",
            "external_request_id": str(uuid.uuid4()),
            "ca_service": "VIETTEL_CA_MOCK"
        }


# =======================================================================
# 3. Helper Functions Chung
# =======================================================================

def verify_signature(data_hash: str, signature: bytes, public_key_pem: str) -> bool:
    """
    Xác minh chữ ký trên hash của tài liệu.
    """
    try:
        # Tải Public Key từ PEM string
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode('utf-8'),
            backend=default_backend()
        )

        # Dữ liệu cần kiểm tra là hash của file
        hash_bytes = bytes.fromhex(data_hash)

        # Thiết lập Padding PSS
        verifier = public_key.verifier(
            signature,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )

        verifier.update(hash_bytes)
        # Hàm verify sẽ raise exception nếu signature không hợp lệ
        verifier.verify()

        return True

    except Exception as e:
        # Lỗi InvalidSignature hoặc key không hợp lệ
        print(f"Xác minh chữ ký thất bại: {e}")
        return False


# Khởi tạo các service
internal_signer = InternalSigner()
external_ca_service = ExternalCAService()
