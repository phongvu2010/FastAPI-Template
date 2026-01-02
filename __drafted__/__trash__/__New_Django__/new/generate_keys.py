import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# --- Cấu hình ---
KEY_SIZE = 3072  # Tương đương -pkeyopt rsa_keygen_bits:3072
PUBLIC_EXPONENT = 65537
OUTPUT_DIR = "secrets"
PRIVATE_KEY_FILE = os.path.join(OUTPUT_DIR, "internal_private_key.pem")
PUBLIC_KEY_FILE = os.path.join(OUTPUT_DIR, "internal_public_key.pem")

def generate_rsa_key_pair():
    # 1. Tạo thư mục 'secrets' (tương đương 'mkdir secrets')
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Đã tạo thư mục: {OUTPUT_DIR}")

    # 2. Tạo private key (tương đương 'openssl genpkey...')
    print(f"Đang tạo RSA private key ({KEY_SIZE}-bit)...")
    private_key = rsa.generate_private_key(
        public_exponent=PUBLIC_EXPONENT,
        key_size=KEY_SIZE,
        backend=default_backend()
    )

    # 3. Trích xuất public key từ private key
    public_key = private_key.public_key()

    # 4. Serialize và lưu private key
    # Định dạng PKCS#8, không mã hóa (NoEncryption)
    pem_private = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        # Nếu dùng mật khẩu, thay thế NoEncryption() bằng AES256Cbc(b'your_password')
        encryption_algorithm=serialization.NoEncryption()
    )

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(pem_private)
    print(f"Đã lưu private key vào: {PRIVATE_KEY_FILE}")

    # 5. Serialize và lưu public key (tương đương 'openssl rsa -pubout...')
    # Định dạng SubjectPublicKeyInfo (đây là định dạng X.509 chuẩn)
    pem_public = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(pem_public)
    print(f"Đã lưu public key vào: {PUBLIC_KEY_FILE}")

    print("\nHoàn tất việc tạo cặp key RSA.")

if __name__ == "__main__":
    generate_rsa_key_pair()
