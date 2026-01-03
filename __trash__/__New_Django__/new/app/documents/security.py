from django.conf import settings
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key

def sign_hash(hash_bytes: bytes) -> bytes:
    """
    Ký vào hash (bytes) bằng Private Key nội bộ.
    """
    if not settings.SIGNING_PRIVATE_KEY:
        raise Exception("Không tìm thấy Private Key để ký.")

    private_key = load_pem_private_key(
        settings.SIGNING_PRIVATE_KEY,
        password=None
    )
    
    signature = private_key.sign(
        hash_bytes,
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    return signature

def get_public_key_pem() -> str:
    """
    Lấy nội dung PEM của Public Key nội bộ.
    """
    if not settings.SIGNING_PUBLIC_KEY_PEM:
        raise Exception("Không tìm thấy Public Key.")
    return settings.SIGNING_PUBLIC_KEY_PEM
