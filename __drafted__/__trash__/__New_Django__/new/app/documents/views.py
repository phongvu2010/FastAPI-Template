from django.shortcuts import render
from django.http import FileResponse, Http404
from rest_framework import generics, views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction, models
from django.shortcuts import get_object_or_404
import hashlib
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa

from .models import Document, DocumentVersion, Signature
from .serializers import (
    DocumentCreateSerializer, DocumentDetailSerializer, RejectSerializer, ExternalSignedUploadSerializer
)
from .permissions import IsSender, IsCheckerOrAdmin, IsManagerOrAdmin
from .utils import create_audit
from .security import sign_hash, get_public_key_pem
from .tasks import verify_hash_task, send_notification_task # Import tasks

# Helper function (tạm thời, nên đưa ra utils riêng)
def calculate_sha256(file_obj):
    """Tính SHA256 cho file[cite: 98, 157]."""
    file_obj.seek(0)
    sha256_hash = hashlib.sha256()
    for chunk in file_obj.chunks():
        sha256_hash.update(chunk)
    file_obj.seek(0)
    return sha256_hash.hexdigest()

# 1. API Upload (SENDER)
class DocumentUploadView(generics.CreateAPIView):
    queryset = Document.objects.all()
    serializer_class = DocumentCreateSerializer
    permission_classes = [IsAuthenticated, IsSender]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data.pop('file')
        notes = serializer.validated_data.pop('notes', '')

        try:
            with transaction.atomic():
                # 1. Tạo Document
                document = Document.objects.create(
                    creator=request.user,
                    title=serializer.validated_data['title'],
                    metadata=serializer.validated_data.get('metadata', {}),
                    status="PENDING"
                )

                # 2. Tính hash và tạo DocumentVersion
                file_hash = calculate_sha256(uploaded_file)

                dv = DocumentVersion.objects.create(
                    document=document,
                    uploaded_by=request.user,
                    file=uploaded_file,
                    file_hash=file_hash,
                    version_number=1,
                    notes=notes
                )

                # 3. Ghi AuditLog
                create_audit(
                    actor=request.user,
                    action="UPLOAD",
                    document=document,
                    document_version=dv,
                    details={"filename": uploaded_file.name, "hash": file_hash}
                )

                # GỌI CELERY TASKS
                # 1. Bắt đầu xác thực hash bất đồng bộ
                verify_hash_task.delay(str(dv.id))

                # 2. Gửi thông báo cho Checker (ví dụ: Admin là checker)
                checker_emails = ['admin@domain.com', 'checker@domain.com'] # Lấy danh sách email từ DB
                subject = f"Hồ sơ mới cần duyệt: {document.title}"
                message = f"User {request.user.email} vừa upload hồ sơ '{document.title}' (v1). Vui lòng duyệt."

                # Gửi thông báo cho từng Checker
                for email in checker_emails:
                    send_notification_task.delay(
                        email,
                        subject,
                        message,
                        action="NOTIFY_CHECKER_NEW_UPLOAD",
                        document_id=str(document.id)
                    )

            headers = self.get_success_headers(serializer.data)
            # Trả về data của Document chi tiết
            detail_serializer = DocumentDetailSerializer(document)
            return Response(detail_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 2. API Xem chi tiết (All roles)
class DocumentDetailView(generics.RetrieveAPIView):
    queryset = Document.objects.all().prefetch_related('versions', 'creator')
    serializer_class = DocumentDetailSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

# 3. API Approve (CHECKER)
class ApproveVersionView(views.APIView):
    permission_classes = [IsAuthenticated, IsCheckerOrAdmin]

    def post(self, request, id, vid, *args, **kwargs):
        document = get_object_or_404(Document, id=id)
        version = get_object_or_404(DocumentVersion, id=vid, document=document)

        if document.status != "PENDING":
             return Response(
                {"error": "Tài liệu không ở trạng thái PENDING."},
                status=status.HTTP_400_BAD_REQUEST
             )

        with transaction.atomic():
            document.status = "APPROVED_FOR_SIGNING"
            document.approved_version = version
            document.save()

            # Ghi AuditLog
            create_audit(
                actor=request.user,
                action="APPROVE",
                document=document,
                document_version=version
            )

        return Response(
            {"status": "APPROVED_FOR_SIGNING"},
            status=status.HTTP_200_OK
        )

# 4. API Reject (CHECKER)
class RejectDocumentView(views.APIView):
    permission_classes = [IsAuthenticated, IsCheckerOrAdmin]

    def post(self, request, id, *args, **kwargs):
        document = get_object_or_404(Document, id=id)

        if document.status != "PENDING":
             return Response(
                {"error": "Tài liệu không ở trạng thái PENDING."},
                status=status.HTTP_400_BAD_REQUEST
             )

        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reason = serializer.validated_data['reason']

        with transaction.atomic():
            document.status = "REJECTED"
            document.approved_version = None
            document.save()

            # Ghi AuditLog
            create_audit(
                actor=request.user,
                action="REJECT",
                document=document,
                details={"reason": reason}
            )
        
        return Response({"status": "REJECTED"}, status=status.HTTP_200_OK)

# 5. API Download File (MANAGER)
class DownloadApprovedFileView(views.APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def get(self, request, id, *args, **kwargs):
        document = get_object_or_404(Document, id=id)

        if document.status != "APPROVED_FOR_SIGNING":
            return Response(
                {"error": "Tài liệu chưa được duyệt hoặc đã ký."},
                status=status.HTTP_400_BAD_REQUEST
            )

        version = document.approved_version
        if not version:
            return Response(
                {"error": "Không tìm thấy phiên bản được duyệt."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Bước quan trọng: Xác thực HASH trước khi cho tải
        computed_hash = calculate_sha256(version.file)
        if computed_hash != version.file_hash:
            create_audit(
                actor=request.user,
                action="HASH_VERIFIED_FAIL",
                document=document,
                document_version=version,
                details={"computed": computed_hash, "stored": version.file_hash}
            )
            return Response(
                {"error": "Xác thực file thất bại! Hash không khớp."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        # Ghi Audit Log
        create_audit(
            actor=request.user,
            action="DOWNLOAD_FOR_SIGNING",
            document=document,
            document_version=version
        )

        # return FileResponse(version.file.open('rb'), as_attachment=True, filename=version.file.name.split('/')[-1])

        # ------------------------------------------------------------------
        # THAY THẾ FileResponse bằng việc trả về Signed URL
        # ------------------------------------------------------------------
        try:
            # FileField.url tự động trả về Signed URL khi PRESIGNED_URLS = True
            signed_url = version.file.url

            return Response(
                {"status": "SUCCESS", "signed_download_url": signed_url},
                status=status.HTTP_200_OK
            )
        except Exception as e:
             return Response(
                {"error": f"Không thể tạo Signed URL: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# 6. API Ký Nội Bộ (MANAGER)
class SignInternalView(views.APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, id, *args, **kwargs):
        document = get_object_or_404(Document, id=id)

        if document.status != "APPROVED_FOR_SIGNING":
            return Response(
                {"error": "Tài liệu không ở trạng thái 'APPROVED_FOR_SIGNING'."},
                status=status.HTTP_400_BAD_REQUEST
            )

        version = document.approved_version
        if not version:
            return Response({"error": "Không tìm thấy phiên bản được duyệt."}, status=status.HTTP_404_NOT_FOUND)

        try:
            with transaction.atomic():
                hash_hex = version.file_hash
                hash_bytes = bytes.fromhex(hash_hex)

                signature_blob = sign_hash(hash_bytes)
                public_key_pem = get_public_key_pem()

                # 2. Tạo đối tượng Signature
                sig = Signature.objects.create(
                    document_version=version,
                    signer=request.user,
                    sig_type="INTERNAL",
                    signature_blob=signature_blob,
                    public_key=public_key_pem
                )

                # 3. Cập nhật trạng thái Document
                document.status = "COMPLETED_INTERNAL"
                document.save()

                # 4. Ghi AuditLog
                create_audit(
                    actor=request.user,
                    action="SIGNED_INTERNAL",
                    document=document,
                    document_version=version,
                    details={"signature_id": str(sig.id)}
                )

            return Response(
                {"status": "COMPLETED_INTERNAL", "signature_id": sig.id},
                status=status.HTTP_201_CREATED
            )
        except Exception as e:
            return Response({"error": f"Lỗi ký: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 7. API Xác Thực Chữ Ký (Public)
class VerifySignatureView(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, id, *args, **kwargs):
        sig = get_object_or_404(Signature, id=id)
        version = sig.document_version

        computed_hash = calculate_sha256(version.file)

        if computed_hash != version.file_hash:
            return Response({"verified": False, "error": "File hash mismatch!"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            public_key = rsa.PublicKey.from_pem(sig.public_key.encode('utf-8'))
            hash_bytes = bytes.fromhex(version.file_hash)

            public_key.verify(
                sig.signature_blob,
                hash_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )

            return Response({"verified": True, "signed_at": sig.created_at, "signer": sig.signer.email if sig.signer else "External"}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({"verified": False, "error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# 8. API Upload File Đã Ký Ngoài (MANAGER/SENDER)
class UploadExternalSignedView(views.APIView):
    # Tạm thời chỉ cho Manager/Admin làm, có thể mở rộng cho SENDER nếu có ủy quyền
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

    def post(self, request, id, *args, **kwargs):
        document = get_object_or_404(Document, id=id)

        if document.status != "APPROVED_FOR_SIGNING":
            return Response(
                {"error": "Tài liệu không ở trạng thái 'APPROVED_FOR_SIGNING' để ký ngoài."},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = ExternalSignedUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        signed_file = serializer.validated_data['signed_file']
        certificate = serializer.validated_data.get('certificate', '')
        meta = serializer.validated_data.get('meta', {})

        try:
            with transaction.atomic():
                # 1. Tính hash cho file mới (đã ký)
                new_file_hash = calculate_sha256(signed_file)

                # 2. Tạo phiên bản mới (Version + 1)
                latest_version_number = document.versions.aggregate(models.Max('version_number'))['version_number__max'] or 0
                new_version_number = latest_version_number + 1

                dv = DocumentVersion.objects.create(
                    document=document,
                    uploaded_by=request.user,
                    file=signed_file,
                    file_hash=new_file_hash,
                    version_number=new_version_number,
                    notes=f"File được ký ngoài (External Signature), dựa trên v{document.approved_version.version_number if document.approved_version else 'N/A'}"
                )

                # 3. Tạo đối tượng Signature
                # Chú ý: Ở đây ta chỉ lưu metadata, không lưu signature_blob/hash được ký
                # vì chữ ký đã được nhúng trong file PDF (PAdES/CAdES).
                # Logic xác thực sẽ cần một bước xử lý PDF chuyên biệt (tùy chọn)
                sig = Signature.objects.create(
                    document_version=dv,
                    signer=None, # Signer là bên ngoài (external), không phải user hệ thống
                    sig_type="EXTERNAL",
                    # Lưu hash của file đã ký
                    signature_blob=bytes.fromhex(new_file_hash),
                    public_key=certificate, # Dùng trường này để lưu chứng thư (nếu có)
                    meta=meta
                )

                # 4. Cập nhật trạng thái Document
                document.status = "COMPLETED_EXTERNAL"
                document.approved_version = dv # Phiên bản đã ký là phiên bản được duyệt mới
                document.save()

                # 5. Ghi AuditLog
                create_audit(
                    actor=request.user,
                    action="UPLOAD_SIGNED_EXTERNAL",
                    document=document,
                    document_version=dv,
                    details={"signature_id": str(sig.id), "original_hash": document.approved_version.file_hash if document.approved_version else 'N/A', "new_hash": new_file_hash}
                )

            return Response(
                {"status": "COMPLETED_EXTERNAL", "version_id": dv.id, "signature_id": sig.id},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": f"Lỗi upload file đã ký: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
