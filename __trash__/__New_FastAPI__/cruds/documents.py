from datetime import datetime
from sqlalchemy.orm import Session
from typing import Optional

# Import models và schemas
from models.documents import Document, DocumentVersion, AuditLog
from models.users import User
from schemas.documents import DocumentCreate

# Import tiện ích
from utils.file_handler import save_file
# Bạn sẽ cần tạo file này:
# from cruds.users import get_user_by_id

# --- HÀM HỖ TRỢ CHUNG ---
def create_audit_log(
    db: Session,
    document_id: int,
    user_id: int,
    action: str,
    details: str,
    related_version_id: Optional[int] = None
) -> AuditLog:
    """Tạo một bản ghi Audit Log cho mọi sự kiện quan trọng."""
    db_log = AuditLog(
        document_id=document_id,
        user_id=user_id,
        action=action,
        details=details,
        related_version_id=related_version_id
    )
    db.add(db_log)
    # Không commit ở đây, để hàm gọi ngoài quyết định commit transaction.
    return db_log

def get_document_by_id(db: Session, doc_id: int) -> Optional[Document]:
    """Tìm kiếm hồ sơ theo ID."""
    return db.query(Document).filter(Document.id == doc_id).first()

# --- HÀM CRUD CHÍNH (LOGIC NGHIỆP VỤ) ---
def create_document_and_initial_version(
    db: Session,
    doc_data: DocumentCreate,
    uploader: User,
    file_data: bytes,
    file_name: str
) -> Document:
    """
    1. Tạo Document (Hồ sơ) mới.
    2. Lưu file vật lý và tạo DocumentVersion (Phiên bản 1).
    3. Cập nhật current_version_id và ghi Audit Log.
    """
    # 1. Tạo Document Code tạm thời dựa trên thời gian và phòng ban
    doc_code = f"{uploader.dept_code}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # 2. Lưu file vật lý và lấy path/hash
    version_filename = f"V1_{file_name}"
    relative_path, file_hash = save_file(
        file_data=file_data,
        dept_code=uploader.dept_code,
        doc_code=doc_code,
        version_filename=version_filename
    )

    # 3. Tạo Document (Hồ sơ)
    db_doc = Document(
        title=doc_data.title,
        document_code=doc_code,
        uploader_id=uploader.id,
        inspector_id=doc_data.inspector_id,
        signer_id=doc_data.signer_id,
        status="SUBMITTED"
    )
    db.add(db_doc)
    db.flush() # Lấy db_doc.id trước khi commit

    # 4. Tạo DocumentVersion (Phiên bản 1)
    db_version = DocumentVersion(
        document_id=db_doc.id,
        version_number=1,
        relative_path=relative_path,
        file_hash=file_hash,
        action_description="Nộp bản gốc",
        uploaded_by_id=uploader.id
    )
    db.add(db_version)
    db.flush() # Lấy db_version.id

    # 5. Cập nhật current_version_id
    db_doc.current_version_id = db_version.id

    # 6. Ghi Audit Log
    create_audit_log(
        db,
        db_doc.id,
        uploader.id,
        "SUBMIT",
        "Hồ sơ được nộp lần đầu.",
        db_version.id
    )

    db.commit()
    db.refresh(db_doc)
    return db_doc

def reject_document(db: Session, doc: Document, user: User, reason: str) -> Document:
    """
    Người Kiểm tra (Inspector) từ chối hồ sơ.
    """
    # 1. Kiểm tra quyền (Đã được kiểm tra ở lớp API nhưng nên kiểm tra lại)
    if doc.inspector_id != user.id:
        raise ValueError("Người dùng không phải là người kiểm tra của hồ sơ này.")

    # 2. Cập nhật trạng thái và ghi Log
    doc.status = "REJECTED_BY_INSPECTOR"

    create_audit_log(
        db,
        doc.id,
        user.id,
        "REJECT",
        f"Từ chối hồ sơ. Lý do: {reason}",
        doc.current_version_id
    )

    db.commit()
    db.refresh(doc)
    return doc

def create_new_version_on_resubmit(
    db: Session,
    doc: Document,
    uploader: User,
    file_data: bytes,
    file_name: str
) -> Document:
    """
    Người nộp sửa file và nộp lại sau khi bị từ chối.
    """
    # 1. Kiểm tra quyền
    if doc.uploader_id != uploader.id:
        raise ValueError("Người dùng không phải là người nộp hồ sơ này.")

    # 2. Xác định Version Number mới
    last_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == doc.id
    ).order_by(DocumentVersion.version_number.desc()).first()

    new_version_number = last_version.version_number + 1 if last_version else 1

    # 3. Lưu file vật lý
    version_filename = f"V{new_version_number}_{file_name}"
    relative_path, file_hash = save_file(
        file_data=file_data,
        dept_code=uploader.dept_code,
        doc_code=doc.document_code,
        version_filename=version_filename
    )

    # 4. Tạo DocumentVersion mới
    db_version = DocumentVersion(
        document_id=doc.id,
        version_number=new_version_number,
        relative_path=relative_path,
        file_hash=file_hash,
        action_description="Nộp lại sau khi sửa lỗi",
        uploaded_by_id=uploader.id
    )
    db.add(db_version)
    db.flush()

    # 5. Cập nhật Document: Trạng thái và Version hiện tại
    doc.status = "SUBMITTED" # Quay lại trạng thái chờ duyệt
    doc.current_version_id = db_version.id

    # 6. Ghi Log
    create_audit_log(
        db,
        doc.id,
        uploader.id,
        "RESUBMIT",
        "Hồ sơ được nộp lại sau khi bị từ chối.",
        db_version.id
    )

    db.commit()
    db.refresh(doc)
    return doc

def internal_sign_document(db: Session, doc: Document, inspector: User, signed_file_data: bytes) -> Document:
    """
    Người Kiểm tra ký nháy (Internal Sign).
    """
    # 1. Kiểm tra quyền
    if doc.inspector_id != inspector.id:
        raise ValueError("Người dùng không phải là người kiểm tra.")

    # 2. Xác định Version Number mới (ký nháy thường tạo ra version phụ)
    last_version = doc.current_version
    new_version_number = last_version.version_number + 0.1 # Ví dụ: 1 -> 1.1

    # 3. Lưu file đã ký nháy
    version_filename = f"V{new_version_number}_internally_signed.pdf"
    relative_path, file_hash = save_file(
        file_data=signed_file_data,
        dept_code=inspector.dept_code,
        doc_code=doc.document_code,
        version_filename=version_filename
    )

    # 4. Tạo DocumentVersion mới
    db_version = DocumentVersion(
        document_id=doc.id,
        version_number=new_version_number,
        relative_path=relative_path,
        file_hash=file_hash,
        action_description="Ký nháy bởi Người kiểm tra",
        uploaded_by_id=inspector.id,
        is_signed_internally=True # Đánh dấu đã ký nháy
    )
    db.add(db_version)
    db.flush()

    # 5. Cập nhật Document
    doc.status = "INTERNALLY_SIGNED" # Chuyển sang trạng thái chờ sếp
    doc.current_version_id = db_version.id

    # 6. Ghi Log
    create_audit_log(
        db,
        doc.id,
        inspector.id,
        "INTERNAL_SIGN",
        "Hồ sơ đã được ký nháy và chuyển cho Sếp.",
        db_version.id
    )

    db.commit()
    db.refresh(doc)
    return doc

# Bạn cần thêm các hàm tương tự cho:
# - upload_externally_signed_file (Tạo V mới, chuyển status sang VALIDATING, gọi Celery task)
# - final_internal_sign (Logic ký nháy hoàn tất, chuyển status sang COMPLETED_INTERNAL)





# from ..tasks import validate_signature_task

# def create_document_with_version(
#     db: Session,
#     doc_data: documents.DocumentCreate,
#     uploader: models.User,
#     file_data: bytes,
#     file_hash: str,
#     relative_path: str
# ) -> models.Document:
#     # Tạo Document
#     doc_code = f"{uploader.dept_code}-{datetime.datetime.now().timestamp()}" # Tạo mã tạm
#     db_doc = models.Document(
#         title=doc_data.title,
#         document_code=doc_code,
#         uploader_id=uploader.id,
#         inspector_id=doc_data.inspector_id,
#         signer_id=doc_data.signer_id,
#         status="SUBMITTED"
#     )
#     db.add(db_doc)
#     db.flush() # Lấy ID của db_doc

#     # Tạo DocumentVersion
#     db_version = models.DocumentVersion(
#         document_id=db_doc.id,
#         version_number=1,
#         relative_path=relative_path,
#         file_hash=file_hash,
#         action_description="Bản gốc",
#         uploaded_by_id=uploader.id
#     )
#     db.add(db_version)
#     db.flush() # Lấy ID của db_version

#     # Cập nhật lại document
#     db_doc.current_version_id = db_version.id

#     # Ghi Log
#     db_log = models.AuditLog(
#         document_id=db_doc.id,
#         user_id=uploader.id,
#         action="SUBMIT",
#         details="Nộp hồ sơ lần đầu"
#     )
#     db.add(db_log)

#     db.commit()
#     db.refresh(db_doc)
#     return db_doc
