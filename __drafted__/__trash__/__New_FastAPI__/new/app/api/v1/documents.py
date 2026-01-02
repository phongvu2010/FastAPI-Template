import json # Để parse metadata JSON từ Form
import uuid
from fastapi import (
    APIRouter, Depends, UploadFile, File, Form, HTTPException, status, Path, Query
)
# Thư viện để trả về file stream
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any

# =======================================================================
# 1. Imports Dependency Functions
# =======================================================================
from ...db.base import get_db # Hàm lấy DB Session

# RBAC Dependencies
from ...core.security import is_checker, is_manager, get_current_active_user 

# Dependency Injection cho Services (Khởi tạo ở main.py)
from ...main import get_document_service, get_storage_service 

# Type Hints cho Services
from ...services.document_service import DocumentService
from ...services.storage_service import AbstractStorageService # Dùng Abstract Class

# Import models và schemas
from ...db import schemas, models

# =======================================================================
# 2. Schemas
# =======================================================================

# --- Pydantic Schema cho Request Body ---
# Cần thêm vào schemas.py, nhưng để đơn giản, ta định nghĩa tạm ở đây
class DocumentReview(schemas.BaseModel):
    """Schema cho input của request xét duyệt (approve/reject)"""
    notes: Optional[str] = Field(None, description="Lý do xét duyệt/từ chối.")

# Class DocumentReview đã định nghĩa ở phần trước (có trường 'reason' -> đổi tên thành 'notes')
# Chúng ta có thể dùng một schema mới để rõ ràng hơn:
class DocumentSign(schemas.BaseModel):
    """Schema cho input của request ký số"""
    notes: Optional[str] = Field(None, description="Ghi chú về chữ ký.")


# =======================================================================
# 3. Routers
# =======================================================================

# Khởi tạo router chính cho Document
router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

# Khởi tạo router cho việc tải file (nên được gộp vào router.py chính) (Endpoint công khai không qua Auth)
download_router = APIRouter()


# -----------------------------------------------------------------------
# ENDPOINT: UPLOAD TÀI LIỆU MỚI (SENDER)
# -----------------------------------------------------------------------

@router.post(
    "/upload",
    response_model=schemas.DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="[SENDER] Upload tài liệu mới và tạo phiên bản v1"
)
async def upload_document(
    # Dependencies
    actor: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
    storage_svc: AbstractStorageService = Depends(get_storage_service), # Dependency cho Storage

    # Request Body (Form Data)
    file: UploadFile = File(..., description="File PDF cần upload"),
    title: str = Form(..., description="Tiêu đề hồ sơ"),
    metadata: str = Form("{}", description="Metadata bổ sung (JSON string)"),
):
    """
    Cho phép người dùng (SENDER) upload một file mới.
    Sử dụng doc_service để tạo Document, DocumentVersion (v1) và kiểm tra hash (Ký Nháy).
    """
    try:
        metadata_dict: Dict[str, Any] = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Metadata không hợp lệ (Không phải JSON)")

    document_in = schemas.DocumentCreate(
        title=title,
        metadata=metadata_dict
    )

    try:
        new_doc = await doc_service.create_new_document(
            db=db,
            document_in=document_in,
            file=file,
            actor=actor,
            # TRUYỀN STORAGE SERVICE VÀO HÀM SERVICE
            storage_service=storage_svc
        )
        return new_doc
    except HTTPException:
        # Re-raise HTTPException (dành cho lỗi Ký Nháy 409)
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi hệ thống khi upload: {e}"
        )


# -----------------------------------------------------------------------
# ENDPOINT: XÉT DUYỆT TÀI LIỆU (CHECKER)
# -----------------------------------------------------------------------

# @router.post(
#     "/{document_id}/approve",
#     response_model=schemas.DocumentReadDetail,
#     dependencies=[Depends(is_checker)], # Yêu cầu quyền CHECKER, MANAGER, hoặc ADMIN
#     summary="Phê duyệt tài liệu (CHECKER/MANAGER)"
# )
# def approve_document_endpoint(
#     document_id: uuid.UUID,
#     review_data: DocumentReview, # Dùng để nhận lý do (nếu có)
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(is_checker), # Dùng lại is_checker để lấy user
# ):
#     """
#     Xử lý việc chấp thuận (Approve) một tài liệu đang ở trạng thái PENDING.
#     - Cập nhật trạng thái -> APPROVED_FOR_SIGNING.
#     - Thiết lập approved_version.
#     - Ghi AuditLog.
#     """

#     try:
#         approved_doc = document_service.approve_document(
#             db=db,
#             document_id=document_id,
#             actor=current_user,
#             reason=review_data.reason
#         )

#         return approved_doc

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         # Xử lý lỗi ngoại lệ không mong muốn
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi khi phê duyệt tài liệu: {e}"
#         )

@router.post(
    "/{document_id}/approve",
    response_model=schemas.DocumentRead,
    dependencies=[Depends(is_checker)], # Chỉ CHECKER/MANAGER/ADMIN mới có quyền
    summary="[CHECKER] Xét duyệt và phê duyệt tài liệu"
)
def approve_document(
    document_id: uuid.UUID = Path(..., description="ID của hồ sơ"),
    review_in: DocumentReview,
    actor: models.User = Depends(is_checker),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    Chuyển trạng thái Document sang APPROVED_FOR_SIGNING.
    """
    try:
        updated_doc = doc_service.approve_document(
            db=db,
            document_id=document_id,
            actor=actor,
            notes=review_in.notes
        )
        return updated_doc
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống: {e}")


# -----------------------------------------------------------------------
# ENDPOINT: KÝ SỐ NỘI BỘ (MANAGER)
# -----------------------------------------------------------------------

@router.post(
    "/{document_id}/sign/internal",
    response_model=schemas.DocumentVersionRead,
    dependencies=[Depends(is_manager)], # Chỉ MANAGER/ADMIN mới có quyền
    summary="[MANAGER] Ký số nội bộ bằng Private Key của Server"
)
def sign_document_internal(
    document_id: uuid.UUID = Path(..., description="ID của hồ sơ"),
    sign_in: DocumentSign,
    actor: models.User = Depends(is_manager),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    Thực hiện Ký số Nội bộ (RSA/PSS) lên phiên bản được phê duyệt của tài liệu.
    """
    try:
        # Doc Service sẽ gọi internal_signer để ký, lưu Signature và chuyển trạng thái
        updated_version = doc_service.sign_document_internal(
            db=db,
            document_id=document_id,
            actor=actor,
            notes=sign_in.notes
        )
        return updated_version
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi ký số: {e}")


# -----------------------------------------------------------------------
# ENDPOINT: TẠO URL TẢI XUỐNG CÓ KÝ (SIGNED URL)
# -----------------------------------------------------------------------

@router.get(
    "/{document_id}/download-url",
    summary="Tạo Signed URL để tải xuống phiên bản tài liệu"
)
async def download_document_url(
    document_id: uuid.UUID = Path(..., description="ID của hồ sơ"),
    version: Optional[int] = Query(None, description="Số phiên bản muốn tải (Mặc định: Phiên bản được phê duyệt/mới nhất)"),
    actor: models.User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
    storage_svc: AbstractStorageService = Depends(get_storage_service), # Dependency cho Storage
):
    """
    Tạo một JWT Token có thời hạn ngắn (Signed URL) cho phép tải xuống file.
    Ghi Audit Log cho hành động này.
    """
    try:
        # Doc Service sẽ tìm phiên bản, tạo Audit Log và ủy quyền tạo URL cho Storage Service
        result = await doc_service.get_download_url(
            db=db,
            document_id=document_id,
            version_number=version,
            actor=actor,
            storage_service=storage_svc # TRUYỀN STORAGE SERVICE VÀO HÀM SERVICE
        )
        return result
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi tạo URL tải xuống: {e}"
        )


# -----------------------------------------------------------------------
# ENDPOINT XỬ LÝ TOKEN TẢI XUỐNG (Download Handler) - PUBLIC
# -----------------------------------------------------------------------

@download_router.get(
    "/download",
    # Không cần response_model vì nó trả về FileResponse
    summary="Xử lý Token tải xuống và trả về file"
)
async def download_file_handler(
    token: str = Query(..., description="Signed Token (JWT) được tạo bởi /download-url"),
    # Dependency Injection cho Storage Service (chỉ cần service này)
    storage_svc: AbstractStorageService = Depends(get_storage_service), 
):
    """
    Endpoint công khai này nhận Signed Token, xác minh nó, và trả về file.
    """

    # 1. Xác minh Token và lấy đường dẫn file vật lý (Ủy quyền cho Storage Service)
    try:
        full_file_path, filename = await storage_svc.get_file_for_download(token)
    except HTTPException as e:
        # Bắt các lỗi từ storage_service (Hết hạn, Invalid token, File not found)
        raise e
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Lỗi nội bộ khi xử lý token."
        )

    # 2. Trả về FileResponse
    return FileResponse(
        path=full_file_path,
        filename=filename, # Tên file khi tải về
        media_type='application/pdf' # Giả định file luôn là PDF
    )





# @router.post(
#     "/",
#     response_model=schemas.DocumentReadDetail,
#     status_code=status.HTTP_201_CREATED,
#     summary="Upload tài liệu mới (Bên Gửi - SENDER)"
# )
# async def upload_new_document(
#     # 1. File upload
#     file: UploadFile = File(..., description="File tài liệu (PDF)"),

#     # 2. Các metadata của tài liệu (Sử dụng Form để nhận JSON data cùng với File)
#     document_data_json: str = Form(
#         ...,
#         alias="document_data",
#         description="JSON string chứa title và metadata. Ví dụ: {'title': 'Hợp đồng A', 'metadata': {'department': 'HR'}}"
#     ),

#     # 3. Dependencies
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_active_user),
# ):
#     """
#     Xử lý nghiệp vụ upload tài liệu mới:
#     - Kiểm tra quyền (được xử lý bởi get_current_active_user, nhưng cần CHECKER/MANAGER).
#     - Parse metadata từ JSON string.
#     - Gọi document_service để xử lý lưu file, tính hash, và ghi DB.
#     """

#     # --- Bước 1: Parse và Validate Input ---
#     try:
#         # FastAPI/Forms không tự động parse JSON khi có UploadFile, phải tự parse
#         data = json.loads(document_data_json)

#         # Validate data against Pydantic schema
#         document_in = schemas.DocumentCreate(**data)

#     except (json.JSONDecodeError, ValueError) as e:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail=f"Dữ liệu 'document_data' không hợp lệ hoặc thiếu trường: {e}"
#         )

#     # --- Bước 2: Kiểm tra quyền (RBAC) ---
#     # Chỉ SENDER, CHECKER, MANAGER, ADMIN mới được phép upload.
#     # Giả sử get_current_active_user đã kiểm tra hoạt động.
#     # Nếu chỉ SENDER được upload, ta có thể thêm logic:
#     if current_user.role not in [schemas.UserRole.SENDER, schemas.UserRole.CHECKER, schemas.UserRole.MANAGER, schemas.UserRole.ADMIN]:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="Người dùng không có quyền thực hiện thao tác upload."
#         )

#     # --- Bước 3: Gọi Service Logic ---
#     try:
#         new_document = await document_service.create_new_document(
#             db=db,
#             document_in=document_in,
#             file=file,
#             actor=current_user
#         )

#         # Trả về đối tượng Document đã được tạo
#         return new_document

#     except IOError as e:
#         # Bắt lỗi từ storage_service
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi hệ thống khi xử lý file: {e}"
#         )
#     # Có thể bắt thêm các lỗi DB khác nếu cần

# async def upload_document(
#     # ... (Giữ nguyên các tham số actor, file, title, metadata)
#     doc_service: DocumentService = Depends(get_document_service),
#     storage_svc: AbstractStorageService = Depends(get_storage_service), # Dependency cho Storage
# ):
#     # ...
#     new_doc = await doc_service.create_new_document(
#         db=db,
#         document_in=document_in,
#         file=file,
#         actor=actor,
#         storage_service=storage_svc # TRUYỀN STORAGE SERVICE VÀO
#     )
#     # ... (Phần còn lại của hàm giữ nguyên)

# @router.post(
#     "/{document_id}/reject",
#     response_model=schemas.DocumentReadDetail,
#     dependencies=[Depends(is_checker)], # Yêu cầu quyền CHECKER, MANAGER, hoặc ADMIN
#     summary="Từ chối tài liệu (CHECKER/MANAGER)"
# )
# def reject_document_endpoint(
#     document_id: uuid.UUID,
#     review_data: DocumentReview, # Bắt buộc phải có lý do
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(is_checker), # Dùng lại is_checker để lấy user
# ):
#     """
#     Xử lý việc từ chối (Reject) một tài liệu đang ở trạng thái PENDING.
#     - Yêu cầu phải có lý do (`reason` không được rỗng).
#     - Cập nhật trạng thái -> REJECTED.
#     - Ghi AuditLog.
#     """

#     if not review_data.reason:
#         raise HTTPException(
#             status_code=status.HTTP_400_BAD_REQUEST,
#             detail="Phải cung cấp lý do khi từ chối tài liệu."
#         )

#     try:
#         rejected_doc = document_service.reject_document(
#             db=db,
#             document_id=document_id,
#             actor=current_user,
#             reason=review_data.reason
#         )

#         return rejected_doc

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         # Xử lý lỗi ngoại lệ không mong muốn
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi khi từ chối tài liệu: {e}"
#         )


# # -----------------------------------------------------------------------
# # ENDPOINT KÝ SỐ NỘI BỘ (INTERNAL SIGNING)
# # -----------------------------------------------------------------------

# @router.post(
#     "/{document_id}/sign",
#     response_model=schemas.DocumentReadDetail,
#     dependencies=[Depends(is_manager)], # Yêu cầu quyền MANAGER hoặc ADMIN
#     summary="Ký số nội bộ cho tài liệu đã được phê duyệt (MANAGER/ADMIN)"
# )
# def sign_document_internal_endpoint(
#     document_id: uuid.UUID = Path(..., description="UUID của Tài liệu cần ký"),
#     sign_data: DocumentSign = DocumentSign(), # Dùng để nhận ghi chú
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(is_manager), # Dùng lại is_manager để lấy user
# ):
#     """
#     Xử lý việc ký số nội bộ (RSA/PSS) cho một tài liệu.
#     - Tài liệu phải ở trạng thái APPROVED_FOR_SIGNING.
#     - Gọi document_service.sign_document_internal để thực hiện ký hash và ghi DB.
#     """

#     try:
#         signed_doc = document_service.sign_document_internal(
#             db=db,
#             document_id=document_id,
#             actor=current_user,
#             notes=sign_data.notes
#         )

#         return signed_doc

#     except HTTPException as e:
#         # Bắt các lỗi 400/404 từ Service Layer (ví dụ: trạng thái không hợp lệ)
#         raise e
#     except Exception as e:
#         # Xử lý lỗi ngoại lệ không mong muốn
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi khi thực hiện ký số nội bộ: {e}"
#         )


# # -----------------------------------------------------------------------
# # ENDPOINTS TRUY XUẤT (READ)
# # -----------------------------------------------------------------------

# @router.get(
#     "/{document_id}",
#     response_model=schemas.DocumentReadDetail,
#     summary="Xem chi tiết tài liệu, phiên bản và chữ ký"
# )
# def get_document_detail_endpoint(
#     document_id: uuid.UUID = Path(..., description="UUID của Tài liệu"),
#     db: Session = Depends(get_db),
#     # Chỉ cần xác thực, logic quyền đọc (Creator, Checker, Manager) đã được xử lý trong service
#     current_user: models.User = Depends(get_current_active_user),
# ):
#     """
#     Truy xuất metadata chi tiết của tài liệu.
#     """
#     # NOTE: Logic kiểm tra quyền đọc nên được xử lý trong service layer
#     try:
#         document = document_service.get_document_read_detail(
#             db=db,
#             document_id=document_id
#         )

#         return document

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi khi truy xuất tài liệu: {e}"
#         )

# @router.get(
#     "/{document_id}/download-url",
#     response_model=Dict[str, str], # Trả về download_url và version_number
#     summary="Lấy URL tải xuống an toàn (Signed URL)"
# )
# def get_document_download_url_endpoint(
#     document_id: uuid.UUID = Path(..., description="UUID của Tài liệu"),
#     version: Optional[int] = Query(None, description="Tải phiên bản cụ thể"),
#     db: Session = Depends(get_db),
#     current_user: models.User = Depends(get_current_active_user),
# ):
#     """
#     Lấy Signed URL cho phép client tải file an toàn.
#     """
#     try:
#         download_info = document_service.get_document_download_url(
#             db=db,
#             document_id=document_id,
#             actor=current_user,
#             version_number=version
#         )

#         return download_info

#     except HTTPException as e:
#         raise e
#     except Exception as e:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Lỗi khi tạo URL tải xuống: {e}"
#         )


# # -----------------------------------------------------------------------
# # ENDPOINT XỬ LÝ TOKEN TẢI XUỐNG (Download Handler)
# # -----------------------------------------------------------------------

# @download_router.get(
#     "/download",
#     # Không cần response_model vì nó trả về FileResponse
#     summary="Xử lý Token tải xuống và trả về file"
# )
# def download_file_handler(
#     token: str = Query(..., description="Signed Token (JWT) được tạo bởi /download-url"),
# ):
#     """
#     Endpoint công khai này nhận Signed Token, xác minh nó, và trả về file.
#     """

#     # 1. Xác minh Token và lấy đường dẫn file vật lý
#     try:
#         full_file_path, filename = storage_service.get_file_for_download(token)
#     except HTTPException as e:
#         # Bắt các lỗi từ storage_service (Hết hạn, Invalid token, File not found)
#         raise e
#     except Exception:
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Lỗi nội bộ khi xử lý token."
#         )

#     # 2. Trả về FileResponse
#     return FileResponse(
#         path=full_file_path,
#         filename=filename, # Tên file khi tải về
#         media_type='application/pdf' # Giả định file luôn là PDF
#         # Có thể thêm headers để tăng cường bảo mật (Content-Security-Policy)
#     )

# # --- (Các endpoint GET, PUT, DELETE khác sẽ được thêm ở đây) ---
