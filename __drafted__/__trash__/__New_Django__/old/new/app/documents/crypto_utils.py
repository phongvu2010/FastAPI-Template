from cryptography.hazmat.primitives.asymmetric import utils, rsa, padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
    Encoding,
    PrivateFormat,
    NoEncryption,
    PublicFormat,
)  # Bổ sung PublicFormat
from cryptography import exceptions  # Cần thiết để bắt lỗi InvalidSignature

import os
import base64
from decouple import config

# Lưu ý: Trong môi trường thực tế, Private Key phải được bảo vệ cực kỳ nghiêm ngặt
# (Ví dụ: HSM, hoặc được mã hóa và chỉ giải mã khi cần ký).
# Chúng ta sẽ giả định một cặp khóa được sinh ra và Private Key được lưu trữ an toàn.

# Khóa Giả định (Dùng cho Demo/Phát triển)
# Lấy khóa từ .env
PRIVATE_KEY_PEM = config("INTERNAL_SIGNING_PRIVATE_KEY", None)
PUBLIC_KEY_PEM = config("INTERNAL_SIGNING_PUBLIC_KEY", None)
# Note: PUBLIC_KEY_PEM sẽ được dùng nếu có, nếu không sẽ tính toán lại.


# --- Hàm Tiện ích ---


def get_private_key():
    """Tải Private Key từ biến môi trường."""
    if not PRIVATE_KEY_PEM:
        # NOTE: Trong Production, cần có cơ chế tải khóa an toàn hơn.
        raise ValueError("INTERNAL_SIGNING_PRIVATE_KEY is not configured.")

    return load_pem_private_key(
        PRIVATE_KEY_PEM.encode("utf-8"),
        password=None,  # Giả định khóa không được mã hóa pass-phrase
    )


def get_public_key_pem() -> str:
    """
    Tải Public Key từ biến môi trường.
    Nếu không có, trích xuất từ Private Key (chỉ hoạt động nếu Private Key có).
    """
    # 1. Ưu tiên sử dụng khóa đã cấu hình trong .env (được khuyến nghị)
    if PUBLIC_KEY_PEM:
        return PUBLIC_KEY_PEM

    # 2. Nếu không có Public Key, tính toán lại từ Private Key
    try:
        private_key = get_private_key()
        public_key = private_key.public_key()

        # Trích xuất Public Key sang định dạng PEM
        public_pem = public_key.public_bytes(
            Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
        ).decode()

        # Note: Không lưu trữ vào biến môi trường runtime (config)
        return public_pem
    except ValueError as e:
        # Lỗi nếu Private Key không được cấu hình
        raise ValueError(
            "INTERNAL_SIGNING_PUBLIC_KEY không được cấu hình VÀ không thể trích xuất từ Private Key."
        ) from e


# --- 1. HÀM KÝ SỐ (Giữ nguyên) ---


def sign_data_hash(data_hash: str) -> str:
    """Thực hiện ký số (RSA/PSS) trên Hash của dữ liệu."""
    try:
        private_key = get_private_key()

        # Hash cần ký là Hash SHA-256 của file
        hash_bytes = bytes.fromhex(data_hash)

        # Thực hiện ký với Padding PSS
        signature = private_key.sign(
            hash_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),
        )
        # Trả về chữ ký dưới dạng Base64 string để lưu vào Database (TextField)
        return base64.b64encode(signature).decode("utf-8")
    except Exception as e:
        raise Exception(f"Lỗi khi ký số: {e}")


# --- 2. HÀM XÁC MINH CHỮ KÝ (Giữ nguyên) ---


def verify_data_hash(
    data_hash: str, signature_base64: str, public_key_pem: str
) -> bool:
    """
    Xác minh chữ ký số (RSA/PSS) trên Hash của dữ liệu.
    """
    try:
        # 1. Tải Public Key từ chuỗi PEM
        public_key = load_pem_public_key(public_key_pem.encode("utf-8"))

        # 2. Chuyển đổi Hash và Chữ ký về dạng Bytes
        # Hash phải là bytes.fromhex vì hash ban đầu là hex string
        hash_bytes = bytes.fromhex(data_hash)

        # Chữ ký phải là base64.b64decode vì được lưu trữ dưới dạng Base64 string
        signature_bytes = base64.b64decode(signature_base64)

        # 3. Thực hiện xác minh
        # Nếu xác minh thành công, hàm không raise exception. Nếu thất bại, nó sẽ raise InvalidSignature.
        # Public Key sẽ kiểm tra (Signature, Hash, Thuật toán Padding)
        public_key.verify(
            signature_bytes,
            hash_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256(),  # Thuật toán Hash được sử dụng
        )
        return True
    except exceptions.InvalidSignature:
        # Chữ ký không khớp với Hash và Public Key
        # Lỗi InvalidSignature được raise khi chữ ký không khớp.
        return False
    except ValueError as e:
        # Lỗi nếu định dạng Hash (Hex) hoặc Chữ ký (Base64) không đúng.
        print(f"Lỗi định dạng dữ liệu đầu vào: {e}")
        return False
    except Exception as e:
        # Các lỗi khác (ví dụ: lỗi cấu hình key)
        # Các lỗi khác (ví dụ: định dạng key, base64)
        print(f"Lỗi xác minh khác: {e}")
        return False
