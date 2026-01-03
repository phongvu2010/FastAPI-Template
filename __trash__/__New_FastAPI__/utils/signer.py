# Đây là code ý tưởng (pseudo-code) dùng pyhanko
from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign import validation
from pyhanko.sign.validation import SignatureCoverageLevel, ValidationContext
from pyhanko_certvalidator import ValidationContext

# 1. Bạn cần chuẩn bị một "Trust Store"
# Đây là danh sách các Public Certificate của các Root CA
# mà bạn tin tưởng (ví dụ: của Viettel, VNPT, Ban cơ yếu CP...)
# Bạn có thể lấy chúng từ website của họ.
trust_roots = [...] # Tải các file .pem hoặc .crt

# 2. Tạo Validation Context
val_context = ValidationContext(trust_roots=trust_roots)

# 3. Mở file PDF (V2) mà sếp vừa upload
reader = PdfFileReader(open('file_V2_da_ky.pdf', 'rb'))

# 4. Lấy tất cả chữ ký trong file
all_signatures = reader.embedded_signatures

if not all_signatures:
    # Báo lỗi: File này không có chữ ký số
    raise Exception("File không có chữ ký.")

# 5. Xác thực từng chữ ký
sig = all_signatures[0] # Giả sử chỉ có 1 chữ ký của sếp

print(f"Đang xác thực chữ ký của: {sig.signer_name}")

# Đây là lệnh quan trọng nhất
status = validation.validate_signature(
    sig,
    val_context,
    # Yêu cầu kiểm tra chữ ký bao phủ toàn bộ file
    SignatureCoverageLevel.ENTIRE_DOCUMENT
)

# 6. Kiểm tra kết quả
if status.valid and status.trusted:
    # XÁC THỰC THÀNH CÔNG!
    # Chữ ký hợp lệ VÀ được tin tưởng (từ Root CA của bạn)
    print("Xác thực thành công!")
    # Cập nhật status hồ sơ trong DB -> completed
else:
    # XÁC THỰC THẤT BẠI
    print(f"Lỗi xác thực: {status.summary}")
    # Cập nhật status hồ sơ trong DB -> validation_failed
