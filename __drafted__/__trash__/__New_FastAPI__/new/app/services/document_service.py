import uuid
from fastapi import UploadFile, HTTPException, status
from sqlalchemy import or_ # Import or_ cho query hash check
from sqlalchemy.orm import Session, selectinload # Thêm selectinload
from typing import IO, Optional, Dict, Any

# Import các service khác
from . import audit_service # Xử lý ghi log (Source 5)
from . import storage_service # Xử lý lưu file (Source 5)
from .storage_service import AbstractStorageService # Import Abstract Storage Service

# Import core signing logic
from ..core.signing import internal_signer, ExternalCAService # Lấy InternalSigner instance

# Import models và schemas
from ..db import models, schemas

# Import Celery Tasks (Mới)
from ..worker import tasks # Import module tasks để gọi các task bên trong


class DocumentService:
    """
    Chứa logic nghiệp vụ chính cho việc xử lý Document và DocumentVersion.
    """

    async def create_new_document(
        self,
        db: Session,
        document_in: schemas.DocumentCreate,
        file: UploadFile,
        actor: models.User,
        # NHẬN AbstractStorageService QUA DEPENDENCY INJECTION
        storage_service: AbstractStorageService
    ) -> models.Document:
        """
        Logic cho nghiệp vụ Upload (Source 105).
        1. Lưu file lên storage (dùng storage_service).
        2. Tính toán hash (dùng storage_service).
        3. Tạo Document.
        4. Tạo DocumentVersion (v1).
        5. Ghi AuditLog (dùng audit_service).
        """

        # 1 & 2: Lưu file và tính hash (ủy quyền cho storage_service)
        # storage_service sẽ chịu trách nhiệm streaming file và tính hash (Source 161)
        storage_result = await storage_service.save_file_and_compute_hash(
            file=file,
            actor_id=actor.id
        )
        new_hash = storage_result.file_hash

        # THÊM LOGIC KIỂM TRA KÝ NHÁY TẠI ĐÂY:
        # -----------------------------------------------------------
        # Kiểm tra nếu file hash đã tồn tại trong bất kỳ DocumentVersion nào ĐÃ KÝ
        signed_versions = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.file_hash == new_hash,
            or_(
                models.DocumentVersion.status == schemas.DocumentStatus.COMPLETED_INTERNAL,
                models.DocumentVersion.status == schemas.DocumentStatus.COMPLETED_EXTERNAL
            )
        ).first()

        if signed_versions:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Hồ sơ này đã tồn tại một phiên bản đã được ký số và không thể upload lại."
            )
        # -----------------------------------------------------------

        # 3. Tạo Document (Bảng cha)
        db_document = models.Document(
            title=document_in.title,
            metadata=document_in.metadata,
            creator_id=actor.id,
            status=schemas.DocumentStatus.PENDING # Trạng thái ban đầu (Source 59)
        )
        db.add(db_document)

        # 4. Tạo DocumentVersion (Bảng con)
        # Đây là phiên bản đầu tiên nên version_number = 1
        db_version = models.DocumentVersion(
            document=db_document, # Liên kết với document vừa tạo
            uploaded_by_id=actor.id,
            file_path=storage_result.file_path,
            file_hash=storage_result.file_hash, # Hash từ storage_service (Source 102)
            version_number=1, # Version đầu tiên (Source 105)
            notes="Phiên bản gốc."
        )
        db.add(db_version)

        # Chúng ta cần commit 2 lần hoặc flush để lấy DB IDs
        # Ở đây, chúng ta commit chung ở cuối (hoặc để API router commit)
        # Tạm thời flush để lấy ID cho AuditLog
        db.flush()

        # 5. Ghi AuditLog (ủy quyền cho audit_service) (Source 105, 126)
        audit_service.create_audit_log(
            db=db,
            actor=actor,
            action="UPLOAD", # (Source 90)
            document=db_document,
            document_version=db_version,
            details={"filename": file.filename, "size": file.size}
        )

        # Commit các thay đổi (Document, DocumentVersion, AuditLog)
        # Lưu ý: Việc commit có thể được xử lý ở tầng API (dependency)
        # nhưng để đơn giản, service có thể tự commit.
        db.commit()

        # Refresh để lấy các relationship (nếu cần)
        db.refresh(db_document)


        # -------------------------------------------------------------------
        # TÍCH HỢP CELERY: KÍCH HOẠT TÁC VỤ NỀN SAU KHI THÀNH CÔNG (MỚI)
        # -------------------------------------------------------------------

        # 1. Thông báo cho người được chỉ định duyệt (ví dụ: tất cả CHECKER)
        # GIẢ ĐỊNH: Ta cần thông báo cho 1 CHECKER. (Cần logic tìm CHECKER trong thực tế)
        tasks.send_notification_task.delay(
            recipient_email="checker@example.com",
            subject=f"[PENDING] Yêu cầu xét duyệt: {db_document.title}",
            body=f"Tài liệu {db_document.title} đang chờ bạn phê duyệt.",
            document_id=str(db_document.id)
        )

        # 2. Thực hiện kiểm tra Hash nền (kiểm tra lại tính toàn vẹn của file)
        tasks.background_hash_verification_task.delay(
            document_version_id_str=str(db_version.id),
            expected_hash=db_version.file_hash
        )

        return db_document


    # =======================================================================
    # LOGIC XÉT DUYỆT (CHECKER REVIEW)
    # =======================================================================

    def approve_document(
        self,
        db: Session,
        document_id: uuid.UUID,
        actor: models.User,
        reason: Optional[str] = None
    ) -> models.Document:
        """
        Logic xét duyệt Chấp thuận (APPROVE).
        1. Kiểm tra trạng thái hiện tại (chỉ PENDING mới được duyệt).
        2. Cập nhật trạng thái thành APPROVED_FOR_SIGNING.
        3. Gán Document.approved_version_id bằng DocumentVersion hiện tại (v1).
        4. Ghi AuditLog.
        """

        # 1. Tìm Document và kiểm tra trạng thái
        db_document = db.get(models.Document, document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        if db_document.status != schemas.DocumentStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Tài liệu đang ở trạng thái '{db_document.status}'. Chỉ PENDING mới được xét duyệt."
            )

        # 2. Cập nhật trạng thái
        db_document.status = schemas.DocumentStatus.APPROVED_FOR_SIGNING

        # 3. Gán approved_version
        # Lấy version mới nhất (v1)
        latest_version = db.query(models.DocumentVersion).filter(
            models.DocumentVersion.document_id == document_id
        ).order_by(
            models.DocumentVersion.version_number.desc()
        ).first()

        if not latest_version:
             raise HTTPException(status_code=500, detail="Lỗi hệ thống: Không tìm thấy phiên bản tài liệu.")

        # Gán phiên bản đã được duyệt (Source 3: Document 1-1 Document.approved_version)
        db_document.approved_version_id = latest_version.id

        # 4. Ghi AuditLog
        audit_service.create_audit_log(
            db=db,
            actor=actor,
            action="APPROVE",
            document=db_document,
            details={"reason": reason or "Không có lý do."}
        )

        db.commit()
        db.refresh(db_document)


        # -------------------------------------------------------------------
        # TÍCH HỢP CELERY: KÍCH HOẠT TÁC VỤ NỀN SAU KHI PHÊ DUYỆT (MỚI)
        # -------------------------------------------------------------------

        # Thông báo cho người tạo Document
        tasks.send_notification_task.delay(
            recipient_email=db_document.creator.email, # Truy cập qua relationship
            subject=f"[APPROVED] Tài liệu của bạn: {db_document.title}",
            body=f"Tài liệu {db_document.title} đã được phê duyệt và sẵn sàng để ký số.",
            document_id=str(db_document.id)
        )

        # Thông báo cho MANAGER/ADMIN (người có quyền ký)
        # GIẢ ĐỊNH: Thông báo cho 1 MANAGER.
        tasks.send_notification_task.delay(
            recipient_email="manager@example.com",
            subject=f"[SIGNING] Tài liệu chờ ký: {db_document.title}",
            body=f"Tài liệu {db_document.title} đã được phê duyệt và chờ ký số.",
            document_id=str(db_document.id)
        )

        return db_document

    def reject_document(
        self,
        db: Session,
        document_id: uuid.UUID,
        actor: models.User,
        reason: str
    ) -> models.Document:
        """
        Logic xét duyệt Từ chối (REJECT).
        1. Kiểm tra trạng thái hiện tại (chỉ PENDING mới được từ chối).
        2. Cập nhật trạng thái thành REJECTED.
        3. YÊU CẦU phải có lý do (reason).
        4. Ghi AuditLog.
        """

        # 1. Tìm Document và kiểm tra trạng thái
        db_document = db.get(models.Document, document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        if db_document.status != schemas.DocumentStatus.PENDING:
            raise HTTPException(
                status_code=400,
                detail=f"Tài liệu đang ở trạng thái '{db_document.status}'. Chỉ PENDING mới được từ chối."
            )

        # 3. Kiểm tra lý do từ chối (REQUIRED)
        if not reason:
            raise HTTPException(
                status_code=400,
                detail="Phải cung cấp lý do khi từ chối tài liệu."
            )

        # 2. Cập nhật trạng thái
        db_document.status = schemas.DocumentStatus.REJECTED

        # 4. Ghi AuditLog
        audit_service.create_audit_log(
            db=db,
            actor=actor,
            action="REJECT",
            document=db_document,
            details={"reason": reason} # Lưu lý do vào audit log
        )

        db.commit()
        db.refresh(db_document)


        # -------------------------------------------------------------------
        # TÍCH HỢP CELERY: KÍCH HOẠT TÁC VỤ NỀN SAU KHI TỪ CHỐI (MỚI)
        # -------------------------------------------------------------------

        # Thông báo cho người tạo Document
        tasks.send_notification_task.delay(
            recipient_email=db_document.creator.email,
            subject=f"[REJECTED] Tài liệu của bạn: {db_document.title}",
            body=f"Tài liệu {db_document.title} đã bị từ chối với lý do: {reason}",
            document_id=str(db_document.id)
        )

        return db_document


    # =======================================================================
    # LOGIC KÝ SỐ NỘI BỘ (INTERNAL SIGNING - MANAGER/ADMIN)
    # =======================================================================

    def sign_document_internal(
        self,
        db: Session,
        document_id: uuid.UUID,
        actor: models.User,
        notes: Optional[str] = None
    ) -> models.Document:
        """
        Logic Ký số nội bộ (RSA/PSS) cho phiên bản đã được phê duyệt.
        (Chỉ áp dụng cho các tài liệu ở trạng thái APPROVED_FOR_SIGNING).
        1. Kiểm tra trạng thái và tìm approved_version.
        2. Ký hash của approved_version bằng internal_signer.
        3. Tạo bản ghi Signature mới.
        4. Cập nhật trạng thái Document (nếu cần).
        5. Ghi AuditLog.
        """

        # 1. Tìm Document và kiểm tra trạng thái
        db_document = db.get(models.Document, document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        if db_document.status != schemas.DocumentStatus.APPROVED_FOR_SIGNING:
            raise HTTPException(
                status_code=400,
                detail=f"Tài liệu đang ở trạng thái '{db_document.status}'. Chỉ APPROVED_FOR_SIGNING mới được ký."
            )

        # Lấy phiên bản đã được phê duyệt (đã gán ở hàm approve_document)
        # SQLAlchemy tự động load relationship: db_document.approved_version
        if not db_document.approved_version:
            # Đây là lỗi logic không nên xảy ra nếu approve_document hoạt động đúng
            raise HTTPException(status_code=500, detail="Lỗi hệ thống: Tài liệu chưa có phiên bản phê duyệt.")

        approved_version = db_document.approved_version

        # 2. Ký Hash (gọi Core Signing Component)
        try:
            # Ký trên SHA-256 Hash của file
            signature_blob = internal_signer.sign_hash(approved_version.file_hash)
            public_key_pem = internal_signer.get_public_key()

        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Lỗi khi thực hiện ký số nội bộ: {e}"
            )

        # 3. Tạo bản ghi Signature mới
        db_signature = models.Signature(
            document_version=approved_version,
            signer=actor, # Người ký chính là actor (current_user)
            sig_type=schemas.SignatureType.INTERNAL,
            signature_blob=signature_blob,
            public_key=public_key_pem, # Lưu Public Key để sau này Verify
            meta={"notes": notes or "Chữ ký nội bộ đầu tiên."}
        )
        db.add(db_signature)

        # 4. Cập nhật trạng thái Document
        # Nếu đây là chữ ký đầu tiên, ta cập nhật trạng thái
        # (Bạn có thể tùy chỉnh logic này nếu muốn ký nhiều bước)
        if not db_document.signatures:
            db_document.status = schemas.DocumentStatus.COMPLETED_INTERNAL

        # 5. Ghi AuditLog
        audit_service.create_audit_log(
            db=db,
            actor=actor,
            action="SIGN_INTERNAL",
            document=db_document,
            document_version=approved_version,
            details={"notes": notes or "Ký số nội bộ"}
        )

        db.commit()
        db.refresh(db_document)


        # -------------------------------------------------------------------
        # TÍCH HỢP CELERY: KÍCH HOẠT TÁC VỤ NỀN SAU KHI KÝ SỐ (MỚI)
        # -------------------------------------------------------------------

        # Thông báo cho người tạo Document và các bên liên quan (ví dụ: CHECKER)
        tasks.send_notification_task.delay(
            recipient_email=db_document.creator.email,
            subject=f"[SIGNED] Tài liệu đã hoàn tất ký số: {db_document.title}",
            body=f"Tài liệu {db_document.title} đã hoàn tất quy trình ký số nội bộ.",
            document_id=str(db_document.id)
        )

        return db_document

    # =======================================================================
    # LOGIC TRUY XUẤT (READ/DOWNLOAD)
    # =======================================================================

    def get_document_read_detail(
        self,
        db: Session,
        document_id: uuid.UUID
    ) -> models.Document:
        """
        Truy xuất chi tiết Document, bao gồm các phiên bản, chữ ký, và người tạo.
        Sử dụng eager loading (selectinload) để tránh N+1 query.
        """
        db_document = db.query(models.Document).options(
            # Eager load các relationships
            selectinload(models.Document.creator),
            selectinload(models.Document.versions).selectinload(models.DocumentVersion.uploaded_by),
            # Load chi tiết Approved Version và các chữ ký của nó
            selectinload(models.Document.approved_version).selectinload(models.DocumentVersion.signatures).selectinload(models.Signature.signer),
            selectinload(models.Document.approved_version).selectinload(models.DocumentVersion.uploaded_by),
        ).filter(models.Document.id == document_id).first()

        if not db_document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        # NOTE: Logic kiểm tra quyền đọc phức tạp hơn có thể được thêm ở đây

        return db_document

    def get_document_download_url(
        self,
        db: Session,
        document_id: uuid.UUID,
        actor: models.User,
        version_number: Optional[int] = None # Cho phép tải phiên bản cụ thể
    ) -> Dict[str, str]:
        """
        Truy xuất URL tải xuống an toàn cho tài liệu (Signed URL hoặc Local Path).
        Áp dụng kiểm tra quyền download (RBAC).
        """

        # 1. Tải Document
        db_document = db.get(models.Document, document_id)
        if not db_document:
            raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")

        # 2. Kiểm tra quyền Download (RBAC)
        # Logic: Chỉ MANAGER/ADMIN mới có quyền download sau khi đã APPROVED/COMPLETED
        # Hoặc người tạo có thể download bản mình upload (cần logic cụ thể hơn)
        allowed_roles = [schemas.UserRole.MANAGER, schemas.UserRole.ADMIN]
        if actor.role not in allowed_roles:
            if actor.id != db_document.creator_id:
                raise HTTPException(status_code=403, detail="Bạn không có quyền tải tài liệu này.")

        # 3. Xác định phiên bản cần tải
        target_version: Optional[models.DocumentVersion] = None

        # Logic chọn phiên bản tải (Ưu tiên bản APPROVED > Bản cụ thể > Bản mới nhất)
        if version_number:
            target_version = db.query(models.DocumentVersion).filter(
                models.DocumentVersion.document_id == document_id,
                models.DocumentVersion.version_number == version_number
            ).first()
        elif db_document.approved_version_id:
            target_version = db.get(models.DocumentVersion, db_document.approved_version_id)
        elif db_document.versions:
             target_version = db.query(models.DocumentVersion).filter(
                models.DocumentVersion.document_id == document_id
            ).order_by(
                models.DocumentVersion.version_number.desc()
            ).first()

        if not target_version:
            raise HTTPException(status_code=404, detail="Không tìm thấy phiên bản tài liệu để tải xuống.")

        # 4. Tạo URL tải xuống an toàn (Ủy quyền cho storage_service)
        # NOTE: Cần cập nhật app/services/storage_service.py để triển khai hàm này
        download_url = storage_service.create_signed_url(
            file_path=target_version.file_path,
            expires_in_seconds=300 # 5 phút (cho Signed URL)
        )

        # 5. Ghi AuditLog hành động Download
        audit_service.create_audit_log(
            db=db,
            actor=actor,
            action="DOWNLOAD",
            document=db_document,
            document_version=target_version,
            details={"version": target_version.version_number}
        )
        db.commit()

        return {
            "version_number": target_version.version_number,
            "download_url": download_url
        }

# Khởi tạo một instance của service để các router có thể import và sử dụng
document_service = DocumentService()
