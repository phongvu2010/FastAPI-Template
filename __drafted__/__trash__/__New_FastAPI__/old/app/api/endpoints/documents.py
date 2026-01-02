from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from app.schemas import documents
from app.api.dependencies import get_db, get_current_user
from app.cruds import documents
from app.utils.file_handler import save_file, read_file
from app.models import models
from app.tasks.tasks import validate_signature_task # Import Celery task
# from app.signer import sign_internally # (Bạn sẽ cần import hàm ký nháy)

router = APIRouter()

@router.post("/", response_model=documents.Document)
async def create_document(
    title: str = Form(...),
    inspector_id: int = Form(...),
    signer_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint 1: Nộp hồ sơ (Upload file lần đầu)
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Chỉ chấp nhận file PDF.")

    file_data = await file.read()

    # (Tạm thời tạo mã hồ sơ và phòng ban)
    doc_code = f"DOC-{current_user.dept_code}-{datetime.now().timestamp()}"
    dept_code = current_user.dept_code

    # Lưu file
    relative_path, file_hash = save_file(
        file_data=file_data,
        dept_code=dept_code,
        doc_code=doc_code,
        version_filename="V1_original.pdf"
    )

    # Tạo Doc Schema
    doc_create = documents.DocumentCreate(
        title=title,
        inspector_id=inspector_id,
        signer_id=signer_id
    )

    # (Giả sử bạn đã có hàm crud.create_document_with_version)
    # db_doc = crud.create_document_with_version(...)

    # (Tạm thời trả về dữ liệu giả)
    return {"message": "File uploaded, logic DB đang chờ CRUD."}

@router.post("/{doc_id}/reject", status_code=status.HTTP_200_OK)
def reject_document(
    doc_id: int,
    reason: documents.DocumentReject,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint 2: Người kiểm tra (Inspector) trả về hồ sơ
    """
    # 1. Lấy document từ DB
    # doc = db.query(models.Document).filter(models.Document.id == doc_id).first()

    # 2. Kiểm tra quyền: current_user có phải là inspector của doc này?
    # if doc.inspector_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Không có quyền từ chối")

    # 3. Kiểm tra trạng thái: Phải là "SUBMITTED"
    # if doc.status != "SUBMITTED":
    #     raise HTTPException(status_code=400, detail="Hồ sơ không ở trạng thái 'Submitted'")

    # 4. Cập nhật trạng thái
    # doc.status = "REJECTED_BY_INSPECTOR"

    # 5. Ghi Audit Log
    # crud.create_audit_log(db, doc_id, current_user.id, "REJECT", reason.details)

    # 6. Gửi thông báo (Celery task)
    # notify_user_task.delay(doc.uploader_id, f"Hồ sơ bị từ chối: {reason.details}")

    # db.commit()
    return {"message": f"Hồ sơ {doc_id} đã bị từ chối. Lý do: {reason.details}"}

@router.post("/{doc_id}/upload_signed", status_code=status.HTTP_202_ACCEPTED)
async def upload_externally_signed_file(
    doc_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint 3: Sếp (Signer) upload file đã ký
    """
    # 1. Lấy document
    # doc = db.query(models.Document).filter(models.Document.id == doc_id).first()

    # 2. Kiểm tra quyền (phải là Signer)
    # if doc.signer_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Không có quyền")

    # 3. Kiểm tra trạng thái (phải là INTERNALLY_SIGNED)

    # 4. Lưu file (phiên bản mới)
    # (Tương tự logic upload ở trên, tạo V3, V4...)
    # new_version = crud.create_new_version(...)

    # 5. Cập nhật trạng thái hồ sơ
    # doc.status = "VALIDATING"
    # doc.current_version_id = new_version.id
    # db.commit()

    # 6. KÍCH HOẠT CELERY TASK ĐỂ XÁC THỰC
    # validate_signature_task.delay(new_version.id)

    return {"message": "File đã được nhận và đang được xác thực."}

@router.post("/{doc_id}/sign_internally_complete", status_code=status.HTTP_200_OK)
async def sign_internally_complete(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    Endpoint 4: Sếp (Signer) ký nháy và CHỐT hồ sơ ở trạng thái nội bộ.
    Chỉ dùng cho các tài liệu nội bộ, không cần giá trị pháp lý cao.
    """
    # 1. Lấy document
    # doc = db.query(models.Document).filter(models.Document.id == doc_id).first()

    # 2. Kiểm tra quyền và trạng thái
    # if doc.signer_id != current_user.id:
    #     raise HTTPException(status_code=403, detail="Không có quyền ký.")
    # if doc.status != "INTERNALLY_SIGNED":
    #     raise HTTPException(status_code=400, detail="Hồ sơ chưa được kiểm tra hoặc đã hoàn tất.")

    # 3. Ký nội bộ lần cuối (Giả sử bạn có hàm signer.finalize_internal_sign)
    # current_version_path = doc.current_version.relative_path
    # new_relative_path, new_hash = signer.finalize_internal_sign(current_version_path, ...)

    # 4. Cập nhật DB (Tạo phiên bản mới nếu cần ký, hoặc chỉ cập nhật trạng thái)
    # if new_relative_path:
    #     crud.create_new_version(...) # Tạo V2.2 đã ký lần cuối

    # 5. Cập nhật trạng thái cuối cùng
    # doc.status = "COMPLETED_INTERNAL"

    # 6. Ghi Audit Log
    # crud.create_audit_log(db, doc_id, current_user.id, "FINAL_INTERNAL_SIGN", "Hoàn tất hồ sơ bằng chữ ký nội bộ.")

    # db.commit()
    return {"message": f"Hồ sơ {doc_id} đã được hoàn tất bằng chữ ký nội bộ (COMPLETED_INTERNAL)."}
