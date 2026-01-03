from .models import AuditLog

def create_audit(actor, action, document=None, document_version=None, details=None):
    """
    Hàm helper để tạo AuditLog nhất quán.
    """
    AuditLog.objects.create(
        actor=actor,
        action=action,
        document=document,
        document_version=document_version,
        details=details or {}
    )





# documents/utils.py
import hashlib
import base64
import os
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidSignature

# Lấy khóa từ biến môi trường (Cần cấu hình biến môi trường trước khi chạy)
# Trong môi trường production, bạn sẽ lấy từ Vault/Secret Manager
# LƯU Ý: Cần SET hai biến môi trường này trước khi chạy ứng dụng
try:
    SYSTEM_PRIVATE_KEY_PEM = os.environ.get('SYSTEM_PRIVATE_KEY', '').encode('utf-8')
    SYSTEM_PUBLIC_KEY_PEM = os.environ.get('SYSTEM_PUBLIC_KEY', '').encode('utf-8')
except AttributeError:
    # Nếu đang chạy local mà chưa set biến môi trường
    SYSTEM_PRIVATE_KEY_PEM = None 
    SYSTEM_PUBLIC_KEY_PEM = None 

# --- 1. HASH UTILITIES ---

def calculate_sha256_hash(file_path):
    """Tính toán và trả về Hash SHA-256 của file tại đường dẫn cho trước."""
    # Sử dụng with open để đảm bảo file được đóng ngay cả khi có lỗi
    try:
        hasher = hashlib.sha256()
        # Đọc file theo từng khối để xử lý hiệu quả các file lớn
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except FileNotFoundError:
        # Xử lý nếu file không tồn tại
        return None
    except Exception as e:
        # Xử lý các lỗi khác
        print(f"Lỗi khi tính Hash: {e}")
        return None
        
# --- 2. LOGGING UTILITIES ---

def create_audit_log(document, actor, action, details="", old_status=None, new_status=None):
    """Ghi lại một sự kiện AuditLog."""
    from documents.models import AuditLog
    try:
        AuditLog.objects.create(
            document=document,
            actor=actor,
            action=action,
            details=details,
            old_status=old_status,
            new_status=new_status
            # ip_address có thể lấy từ request.META, nhưng để đơn giản, ta sẽ bỏ qua ở đây
        )
    except Exception as e:
        # Quan trọng: Ghi log lỗi nếu không thể ghi AuditLog
        print(f"LỖI HỆ THỐNG: Không thể tạo AuditLog cho {action}. Lỗi: {e}")

# --- 3. CRYPTO UTILITIES (KÝ SỐ) ---

def system_sign_hash(data_hash_hex):
    """Hệ thống sử dụng Private Key để Ký lên Hash của dữ liệu."""
    if not SYSTEM_PRIVATE_KEY_PEM:
        raise Exception("SYSTEM_PRIVATE_KEY chưa được cấu hình hoặc rỗng!")

    # Tải Private Key
    private_key = load_pem_private_key(SYSTEM_PRIVATE_KEY_PEM, password=None) 
        
    # Chuyển Hash Hex sang Bytes
    data_to_sign = bytes.fromhex(data_hash_hex)

    # Thực hiện Ký (PSS Padding là chuẩn an toàn hiện đại)
    signature_bytes = private_key.sign(
        data_to_sign,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256()
    )
    return base64.b64encode(signature_bytes).decode('utf-8') # Trả về Base64

def verify_system_signature(data_hash_hex, signature_base64):
    """Sử dụng Public Key để xác thực chữ ký."""
    if not SYSTEM_PUBLIC_KEY_PEM:
        print("Cảnh báo: PUBLIC_KEY chưa được cấu hình.")
        return False
    
    try:
        # Tải Public Key
        public_key = load_pem_public_key(SYSTEM_PUBLIC_KEY_PEM)

        # Chuyển đổi dữ liệu
        data_to_verify = bytes.fromhex(data_hash_hex)
        signature_bytes = base64.b64decode(signature_base64)

        # Thực hiện Xác thực
        public_key.verify(
            signature_bytes,
            data_to_verify,
            padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
            hashes.SHA256()
        )
        return True
    except InvalidSignature:
        return False # Chữ ký không khớp/dữ liệu đã bị thay đổi
    except Exception as e:
        print(f"Lỗi khi xác thực: {e}")
        return False
