# from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.db import transaction
import hashlib

from .models import Document, DocumentVersion
from .serializers import DocumentUploadSerializer, DocumentReviewSerializer, DocumentSignSerializer
from .utils import calculate_sha256_hash, create_audit_log

class DocumentUploadView(APIView):
    # Sử dụng Django's permission classes (cần cấu hình Authentication)
    # permission_classes = [IsAuthenticated] 

    def post(self, request, *args, **kwargs):
        # Giả định người dùng đã được xác thực
        user = request.user 
        
        # SỬ DỤNG VAI TRÒ (RBAC): Chỉ SENDER mới được phép upload
        # if user.role not in ('SENDER', 'ADMIN'): 
        #     return Response({"error": "Bạn không có quyền tải lên/upload lại hồ sơ."}, 
        #                     status=status.HTTP_403_FORBIDDEN)

        if request.user.role not in ('SENDER', 'ADMIN'): 
            return Response({"error": "Bạn không có quyền tải lên hồ sơ."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentUploadSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file_data = serializer.validated_data['file']
        doc_id = serializer.validated_data.get('document_id')
        title = serializer.validated_data.get('title')

        try:
            with transaction.atomic():
                # --- A. TẠO MỚI HOẶC TÌM KIẾM DOCUMENT ---
                if doc_id:
                    # Cập nhật hồ sơ cũ
                    document = get_object_or_404(Document, pk=doc_id)
                    old_status = document.status
                    
                    # LOGIC BƯỚC 1: KHÔNG THỂ UPLOAD NẾU ĐÃ KÝ NHÁY/DUYỆT
                    if document.status not in ['PENDING', 'REJECTED']:
                        return Response({
                            "error": "Không thể upload lại. Hồ sơ đã được ký nháy hoặc đang trong quá trình hoàn tất."
                        }, status=status.HTTP_403_FORBIDDEN)
                    
                    # Đưa trạng thái về PENDING để chờ duyệt lại
                    document.status = 'PENDING'
                    document.save()
                    
                    # Tăng số phiên bản
                    latest_version = DocumentVersion.objects.filter(document=document).order_by('-version_number').first()
                    new_version_num = latest_version.version_number + 1 if latest_version else 1
                else:
                    # Tạo hồ sơ mới
                    document = Document.objects.create(
                        title=title, 
                        created_by=user, 
                        status='PENDING'
                    )
                    old_status = None
                    new_version_num = 1
                    
                # --- B. TẠO DOCUMENT VERSION VÀ TÍNH HASH ---
                new_version = DocumentVersion(
                    document=document,
                    uploader=user,
                    version_number=new_version_num,
                    file=file_data
                )
                
                # Lưu file vào hệ thống file (MEDIA_ROOT)
                new_version.save() 
                
                # 1. TÍNH HASH SHA-256 (CỐT LÕI BẢO MẬT)
                file_hash = calculate_sha256_hash(new_version.file.path)
                
                if not file_hash:
                    raise Exception("Không thể tính Hash cho file.")

                new_version.file_hash = file_hash
                new_version.save()
                
                # 2. GHI LOG KIỂM TOÁN (AUDITLOG)
                details = f"Tải lên phiên bản V{new_version_num}. Hash: {file_hash[:10]}..."
                create_audit_log(
                    document=document,
                    actor=user,
                    action='UPLOAD_NEW_VERSION',
                    details=details,
                    old_status=old_status,
                    new_status=document.status
                )
                
                return Response({
                    "message": "Upload thành công!",
                    "document_id": document.id,
                    "version": new_version.version_number,
                    "file_hash_preview": file_hash[:10] + "...",
                }, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class DocumentReviewView(APIView):
    # API này sẽ xử lý cả Duyệt (PUT) và Từ chối (POST/PATCH)
    
    def post(self, request, *args, **kwargs):
        # Giả định user đã được xác thực
        user = request.user 

        # --- KIỂM TRA PHÂN QUYỀN (RBAC): Chỉ CHECKER mới được duyệt ---
        if user.role not in ('CHECKER', 'ADMIN'): 
            return Response({"error": "Bạn không có quyền Kiểm tra/Duyệt hồ sơ."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentReviewSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        document = serializer.document 
        reason = serializer.validated_data.get('rejection_reason')
        
        # --- LOGIC DUYỆT (Ký Nháy) ---
        if not reason:
            return self._handle_approval(document, user)
        # --- LOGIC TỪ CHỐI ---
        else:
            return self._handle_rejection(document, user, reason)

    @transaction.atomic
    def _handle_approval(self, document, user):
        """Xử lý hành động Duyệt (Ký nháy)"""
        
        # Lấy phiên bản mới nhất (vừa được SENDER upload)
        latest_version = DocumentVersion.objects.filter(document=document).order_by('-version_number').first()
        
        if not latest_version:
            return Response({"error": "Không tìm thấy phiên bản hồ sơ để duyệt."}, 
                            status=status.HTTP_400_BAD_REQUEST)
                            
        old_status = document.status
        
        # BƯỚC KHÓA HASH (Cốt lõi của việc ký nháy)
        document.approved_version = latest_version
        document.status = 'APPROVED_FOR_SIGNING' # Chuyển trạng thái
        document.save()
        
        # Ghi Log Kiểm toán (AuditLog)
        details = f"Phiên bản V{latest_version.version_number} đã được duyệt. Hash: {latest_version.file_hash[:10]}... đã được khóa."
        create_audit_log(
            document=document,
            actor=user,
            action='SIGNED_INITIALLY',
            details=details,
            old_status=old_status,
            new_status=document.status
        )
        
        # TODO: Gửi thông báo (dùng Celery) cho MANAGER
        
        return Response({
            "message": "Hồ sơ đã được ký nháy và khóa phiên bản. Chuyển sang trạng thái chờ ký chính.",
            "document_id": document.id,
            "approved_version_hash": latest_version.file_hash
        }, status=status.HTTP_200_OK)

    @transaction.atomic
    def _handle_rejection(self, document, user, reason):
        """Xử lý hành động Từ chối"""
        
        old_status = document.status
        document.status = 'REJECTED' # Chuyển trạng thái
        document.save()
        
        # Ghi Log Kiểm toán (AuditLog)
        create_audit_log(
            document=document,
            actor=user,
            action='REJECTED',
            details=f"Từ chối hồ sơ. Lý do: {reason}",
            old_status=old_status,
            new_status=document.status
        )
        
        # TODO: Gửi thông báo (dùng Celery) cho SENDER
        
        return Response({
            "message": "Hồ sơ đã bị từ chối. SENDER có thể upload lại.",
            "document_id": document.id,
            "rejection_reason": reason
        }, status=status.HTTP_200_OK)

class DocumentSignView(APIView):
    def post(self, request, *args, **kwargs):
        # Giả định user đã được xác thực
        user = request.user 

        # --- KIỂM TRA PHÂN QUYỀN (RBAC): Chỉ MANAGER mới được ký chính ---
        if user.role not in ('MANAGER', 'ADMIN'): 
            return Response({"error": "Bạn không có quyền Ký chính hồ sơ."}, 
                            status=status.HTTP_403_FORBIDDEN)

        serializer = DocumentSignSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        document = serializer.document 
        signature_data = serializer.validated_data['signature_data']
        
        return self._handle_final_signing(document, user, signature_data)

    @transaction.atomic
    def _handle_final_signing(self, document, user, signature_data):
        """Xử lý hành động Ký Chính"""
        
        # 1. LẤY PHIÊN BẢN ĐÃ ĐƯỢC CHECKER DUYỆT (approved_version)
        # Vì đã được khóa ở bước trước, document.approved_version không thể là None
        approved_version = document.approved_version 
        
        # 2. KIỂM TRA TÍNH TOÀN VẸN (HASH CHECK)
        # Giả lập việc đọc lại file từ đĩa và tính hash để so sánh
        file_path = approved_version.file.path
        current_hash = self._calculate_file_hash(file_path) # Hàm tính hash giả lập
        
        if current_hash != approved_version.file_hash:
            # Nếu Hash không khớp, hồ sơ đã bị can thiệp!
            old_status = document.status
            document.status = 'TAMPERED'
            document.save()
            
            create_audit_log(
                document=document,
                actor=user,
                action='TAMPER_DETECTED',
                details=f"Hash của file đã bị thay đổi (Hash khóa: {approved_version.file_hash[:10]}... | Hash hiện tại: {current_hash[:10]}...)",
                old_status=old_status,
                new_status=document.status
            )
            return Response({
                "error": "Lỗi Toàn vẹn dữ liệu: File đã bị thay đổi sau khi duyệt. Hành động Ký bị hủy bỏ.",
                "document_id": document.id,
            }, status=status.HTTP_409_CONFLICT) # Code 409: Conflict
            
        # 3. KÝ CHÍNH THỨC VÀ CẬP NHẬT TRẠNG THÁI
        old_status = document.status
        document.status = 'SIGNED_FINAL' # Trạng thái cuối cùng: Đã Ký
        document.save()
        
        # TODO: Lưu chữ ký vào file/metadata của file (sử dụng thư viện ký số thực tế)
        # Hiện tại, ta ghi nhận lại signature_data cho mục đích demo/log
        
        # 4. Ghi Log Kiểm toán (AuditLog)
        details = f"Hồ sơ đã được Ký Chính (Final Signature) bởi MANAGER. Signature Data: {signature_data[:10]}..."
        create_audit_log(
            document=document,
            actor=user,
            action='SIGNED_FINAL',
            details=details,
            old_status=old_status,
            new_status=document.status
        )
        
        # TODO: Gửi thông báo (dùng Celery) cho tất cả các bên liên quan
        
        return Response({
            "message": "Hồ sơ đã được Ký Chính thức và hoàn tất quy trình.",
            "document_id": document.id,
            "status": document.status
        }, status=status.HTTP_200_OK)

    def _calculate_file_hash(self, file_path):
        """
        [GIẢ LẬP] Hàm này sẽ đọc file và tính toán lại SHA256 Hash.
        Trong môi trường production, bạn sẽ dùng hàm này để kiểm tra tính toàn vẹn.
        """
        # Cần xử lý lỗi nếu file không tồn tại
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                # Đọc từng khối (block) để xử lý file lớn
                for chunk in iter(lambda: f.read(4096), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except FileNotFoundError:
            # Trong trường hợp file vật lý đã bị xóa
            return "FILE_NOT_FOUND"



    @transaction.atomic
    def _handle_final_signing(self, document, user): # Bỏ signature_data khỏi tham số
        """Xử lý hành động Ký Chính"""
        
        approved_version = document.approved_version 
        
        # 1. KIỂM TRA TÍNH TOÀN VẸN (HASH CHECK)
        file_path = approved_version.file.path
        current_hash = self._calculate_file_hash(file_path) 
        
        if current_hash != approved_version.file_hash:
            # ... (Logic xử lý TAMPERED vẫn giữ nguyên) ...
            return Response({"error": "Lỗi Toàn vẹn dữ liệu: File đã bị thay đổi..."}, status=status.HTTP_409_CONFLICT)
            
        # 2. THỰC HIỆN KÝ SỐ NỘI BỘ (Chỉ xảy ra khi Hash Check thành công)
        try:
            # Ký lên Hash của phiên bản đã duyệt
            digital_signature = system_sign_hash(approved_version.file_hash) 
        except Exception as e:
            create_audit_log(document, user, 'SIGNING_ERROR', f"Lỗi tạo chữ ký: {e}")
            return Response({"error": "Lỗi hệ thống khi tạo chữ ký số."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 3. LƯU CHỮ KÝ VÀ CẬP NHẬT TRẠNG THÁI
        old_status = document.status
        document.internal_signature = digital_signature # Lưu chữ ký vào DB
        document.status = 'COMPLETED_INTERNAL' # Chuyển sang trạng thái hoàn tất
        document.save()
        
        # 4. Ghi Log Kiểm toán (AuditLog)
        details = f"Hồ sơ đã được Ký Chính thức (Hệ thống). Chữ ký: {digital_signature[:10]}..."
        create_audit_log(
            document=document,
            actor=user,
            action='SIGNED_INTERNAL',
            details=details,
            old_status=old_status,
            new_status=document.status
        )
        
        return Response({
            "message": "Hồ sơ đã được Ký Chính thức và hoàn tất quy trình.",
            "document_id": document.id,
            "status": document.status,
            "signature": digital_signature[:30] + "...",
        }, status=status.HTTP_200_OK)

    # # Chú ý: Cần điều chỉnh `DocumentSignSerializer` để không yêu cầu `signature_data` nữa 
    # # vì hệ thống tự tạo chữ ký, không cần MANAGER gửi lên.
    # # Hoặc, chỉ cần thay đổi View:
    # def post(self, request, *args, **kwargs):
    #     # ... logic kiểm tra quyền
    #     document_id = request.data.get('document_id')
    #     if not document_id:
    #          return Response({"error": "Cần cung cấp document_id."}, status=status.HTTP_400_BAD_REQUEST)
             
    #     # Tải Document và kiểm tra trạng thái ngay tại View
    #     try:
    #         document = Document.objects.get(pk=document_id)
    #     except Document.DoesNotExist:
    #         return Response({"error": "Hồ sơ không tồn tại."}, status=status.HTTP_404_NOT_FOUND)
            
    #     if document.status != 'APPROVED_FOR_SIGNING':
    #          return Response({"error": "Hồ sơ không ở trạng thái chờ ký."}, status=status.HTTP_403_FORBIDDEN)
             
    #     return self._handle_final_signing(document, request.user) # Gọi hàm xử lý Ký
