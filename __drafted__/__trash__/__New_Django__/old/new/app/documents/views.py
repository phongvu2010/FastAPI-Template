from django.shortcuts import render
import hashlib
from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action, api_view
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.http import FileResponse, Http404
from django.db.models import Max
from django.core.files.storage import default_storage

# Import Models và Tiện ích
from .crypto_utils import sign_data_hash, get_public_key_pem, verify_data_hash
from .models import Document, DocumentVersion, AuditLog, User
from .utils import create_audit_log, calculate_sha256_hash, is_allowed_role
from .tasks import send_notification_task
from .serializers import UserSerializer, DocumentSerializer, DocumentVersionSerializer
from accounts.permissions import IsAdmin, IsChecker, IsManager, IsSender 


# --- Permissions Tùy chỉnh ---
class IsAdmin(permissions.BasePermission):
    """
    Chỉ cho phép người dùng có role 'ADMIN' thực hiện hành động (CRUD User).
    """

    def has_permission(self, request, view):
        # Đảm bảo người dùng đã đăng nhập VÀ có role là ADMIN
        return request.user.is_authenticated and request.user.role == "ADMIN"


# ====================================================================
# I. USER MANAGEMENT VIEWSET (Quản lý Người dùng) - Chỉ dành cho ADMIN
# ====================================================================


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint cho phép quản lý (CRUD) các đối tượng User.
    Chỉ có ADMIN mới có quyền truy cập.
    """

    queryset = User.objects.all().order_by("email")
    serializer_class = UserSerializer  # Gán UserSerializer
    permission_classes = [IsAdmin]

    def perform_create(self, serializer):
        # Đây là nơi bạn sẽ xử lý việc tạo người dùng, bao gồm cả việc hash mật khẩu
        # nếu bạn đang tạo người dùng bằng username/password truyền thống.
        # Nếu sử dụng SSO (Google Auth), logic này có thể đơn giản hơn.
        user = serializer.save()
        create_audit_log(
            None,
            self.request.user,
            "USER_CREATED",
            {"target_user": user.email, "role": user.role},
        )

    def perform_update(self, serializer):
        user = serializer.save()
        create_audit_log(
            None,
            self.request.user,
            "USER_UPDATED",
            {"target_user": user.email, "new_role": user.role},
        )

    def perform_destroy(self, instance):
        create_audit_log(
            None,
            self.request.user,
            "USER_DELETED",
            {"target_user": instance.email, "role": instance.role},
        )
        instance.delete()


# ====================================================================
# II. DOCUMENT MANAGEMENT VIEWSET (Quản lý Hồ sơ & Ký số)
# ====================================================================


class DocumentViewSet(viewsets.ModelViewSet):
    # Base Permissions: Chỉ người dùng đã đăng nhập mới được xem
    permission_classes = [permissions.IsAuthenticated]
    queryset = Document.objects.all().select_related('created_by', 'approved_version')
    serializer_class = DocumentSerializer

    # 1. SENDER Upload/Nộp Hồ sơ (create method)
    def create(self, request, *args, **kwargs):
        if not IsSender().has_permission(request, self):
            return Response({"detail": "Chỉ SENDER mới được tạo hồ sơ."}, status=status.HTTP_403_FORBIDDEN)
        
        # [Transaction Logic]: Đảm bảo tạo Document và DocumentVersion là atomic
        with transaction.atomic():
            # Bước 1: Tạo Document (chưa có file/version)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            document = serializer.save(created_by=request.user)
            
            # Bước 2: Xử lý Upload file và tạo DocumentVersion
            if 'file' in request.FILES:
                file_data = request.FILES['file']
                file_hash = calculate_sha256_hash(file_data)
                
                # Kiểm tra hash duy nhất
                if DocumentVersion.objects.filter(file_hash=file_hash).exists():
                    return Response({"detail": "File này đã tồn tại trong hệ thống. Vui lòng chỉnh sửa."}, status=status.HTTP_400_BAD_REQUEST)
                
                # Lưu file và tạo version
                doc_version = DocumentVersion.objects.create(
                    document=document,
                    file=file_data, # FileField sẽ xử lý việc lưu file
                    file_hash=file_hash,
                    version_number=1 # Phiên bản đầu tiên
                )
                
                # Ghi Log
                create_audit_log(document, request.user, 'UPLOAD_V1', {'hash': file_hash, 'version': 1})
            else:
                return Response({"detail": "Thiếu file hồ sơ."}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(self.get_serializer(document).data, status=status.HTTP_201_CREATED)

    # 2. CHECKER: Ký Nháy/Từ chối (review_approve/review_reject)
    @action(detail=True, methods=["post"], url_path="approve")
    def review_approve(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        if not is_allowed_role(request.user, "CHECKER"):
            return Response(
                {"detail": "Chỉ CHECKER được duyệt hồ sơ."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if document.status != "PENDING":
            return Response(
                {
                    "detail": f"Hồ sơ không ở trạng thái PENDING. Trạng thái hiện tại: {document.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        latest_version = document.documentversion_set.order_by(
            "-version_number"
        ).first()
        if not latest_version:
            return Response(
                {"detail": "Lỗi: Không tìm thấy phiên bản tài liệu."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            document.status = "APPROVED_FOR_SIGNING"
            document.approved_version = latest_version
            document.save()

            create_audit_log(
                document,
                request.user,
                "APPROVED",
                {
                    "approved_version": latest_version.version_number,
                    "file_hash": latest_version.file_hash,
                },
            )

            send_notification_task.delay(document.id, "APPROVED")

        return Response(
            {
                "status": document.status,
                "message": f"Hồ sơ đã được CHECKER duyệt (Ký nháy) phiên bản v{latest_version.version_number}.",
            }
        )

    @action(detail=True, methods=["post"], url_path="reject")
    def review_reject(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)
        if not is_allowed_role(request.user, "CHECKER"):
            return Response(
                {"detail": "Chỉ CHECKER được từ chối hồ sơ."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if document.status != "PENDING":
            return Response(
                {
                    "detail": f"Hồ sơ không ở trạng thái PENDING. Trạng thái hiện tại: {document.status}"
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            document.status = "REJECTED"
            document.save()

            create_audit_log(
                document,
                request.user,
                "REJECTED",
                {"reason": request.data.get("reason", "Không rõ")},
            )

        return Response({"status": document.status, "message": "Hồ sơ đã bị từ chối."})

    # ----------------------------------------------------------------
    # 2. ACTION: Ký Nháy/Duyệt (Chỉ cho phép CHECKER)
    # ----------------------------------------------------------------
    @action(detail=True, methods=['post'], permission_classes=[IsChecker])
    def approve_for_signing(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        # Chỉ duyệt khi trạng thái là PENDING và chưa có approved_version
        if document.status != 'PENDING' or document.approved_version is not None:
            return Response({"detail": "Hồ sơ không hợp lệ để duyệt nháy."}, status=status.HTTP_400_BAD_REQUEST)

        # Lấy phiên bản mới nhất chưa được duyệt
        latest_version = document.versions.latest('version_number')

        with transaction.atomic():
            document.approved_version = latest_version
            document.status = 'APPROVED_FOR_SIGNING'
            document.save()

            create_audit_log(document, request.user, 'CHECKER_APPROVED', {'version': latest_version.version_number, 'hash': latest_version.file_hash})

            # Kích hoạt task thông báo
            send_notification_task.delay(document.id, 'APPROVED')

        return Response({"detail": "Hồ sơ đã được ký nháy thành công.", "status": document.status}, status=status.HTTP_200_OK)

    # ----------------------------------------------------------------
    # 3. ACTION: Ký Chính Nội bộ (Chỉ cho phép MANAGER)
    # ----------------------------------------------------------------
    @action(detail=True, methods=['post'], permission_classes=[IsManager])
    def sign_internal(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        if document.status != 'APPROVED_FOR_SIGNING' or document.approved_version is None:
            return Response({"detail": "Hồ sơ chưa được duyệt nháy hoặc đã ký."}, status=status.HTTP_400_BAD_REQUEST)

        approved_version = document.approved_version
        file_hash = approved_version.file_hash

        try:
            # 1. Thực hiện Ký số
            internal_signature = sign_data_hash(file_hash)

            with transaction.atomic():
                # 2. Cập nhật chữ ký và trạng thái
                document.internal_signature = internal_signature
                document.status = 'COMPLETED_INTERNAL'
                document.save()

                # 3. Ghi Log
                create_audit_log(document, request.user, 'SIGNED_INTERNAL', {'hash': file_hash, 'signature': internal_signature[:20] + '...'})

                # 4. Kích hoạt task thông báo
                send_notification_task.delay(document.id, 'COMPLETED_INTERNAL')

            return Response({"detail": "Hồ sơ đã ký chính nội bộ thành công."}, status=status.HTTP_200_OK)
        except ValueError as e:
            create_audit_log(document, request.user, 'SIGN_FAIL', {'error': str(e)})
            return Response({"detail": f"Lỗi ký số: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # 3. MANAGER: Ký Chính Nội bộ (formal_sign_internal)
    @action(detail=True, methods=["post"], url_path="sign-internal")
    def formal_sign_internal(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        if not is_allowed_role(request.user, "MANAGER"):
            return Response(
                {"detail": "Chỉ MANAGER được ký chính."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if document.status != "APPROVED_FOR_SIGNING" or not document.approved_version:
            return Response(
                {"detail": "Hồ sơ chưa được duyệt (APPROVED_FOR_SIGNING)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        approved_version = document.approved_version

        # BƯỚC BẢO MẬT QUAN TRỌNG: Xác thực Hash trước khi Ký
        try:
            with default_storage.open(approved_version.file.name, "rb") as file_on_disk:
                re_calculated_hash = calculate_sha256_hash(file_on_disk)
        except Exception as e:
            create_audit_log(
                document,
                request.user,
                "HASH_VERIFIED_FAIL",
                {"error": f"Lỗi đọc file từ storage: {e}"},
            )
            return Response(
                {"detail": "Lỗi hệ thống: Không thể đọc file để kiểm tra toàn vẹn."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if re_calculated_hash != approved_version.file_hash:
            create_audit_log(
                document,
                request.user,
                "HASH_VERIFIED_FAIL",
                {
                    "expected_hash": approved_version.file_hash,
                    "actual_hash": re_calculated_hash,
                    "version": approved_version.version_number,
                },
            )
            return Response(
                {
                    "detail": "Lỗi toàn vẹn dữ liệu: Hash file trên server không khớp. KHÔNG THỂ KÝ."
                },
                status=status.HTTP_409_CONFLICT,
            )

        # Ký số thành công
        try:
            signature = sign_data_hash(approved_version.file_hash)

            with transaction.atomic():
                document.internal_signature = signature
                document.status = "COMPLETED_INTERNAL"
                document.save()

                create_audit_log(
                    document,
                    request.user,
                    "SIGNED_INTERNAL",
                    {
                        "signed_hash": approved_version.file_hash,
                        "version": approved_version.version_number,
                    },
                )

            send_notification_task.delay(document.id, "COMPLETED_INTERNAL")

            return Response(
                {
                    "status": document.status,
                    "message": "Hồ sơ đã được ký chính nội bộ thành công.",
                    "signature": signature,
                }
            )

        except Exception as e:
            return Response(
                {"detail": f"Lỗi Ký số: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    # 4. MANAGER: Upload File đã Ký ngoài (upload_signed_external)
    @action(detail=True, methods=["post"], url_path="upload-signed-external")
    def upload_signed_external(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        if not is_allowed_role(request.user, "MANAGER"):
            return Response(
                {"detail": "Chỉ MANAGER được upload file đã ký ngoài."},
                status=status.HTTP_403_FORBIDDEN,
            )

        signed_file = request.FILES.get("file")
        if not signed_file:
            return Response(
                {"detail": "Thiếu file PDF đã ký (external)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_file_hash = calculate_sha256_hash(signed_file)

        with transaction.atomic():
            max_version_result = document.documentversion_set.aggregate(
                max_version=Max("version_number")
            )
            new_version_number = (max_version_result["max_version"] or 0) + 1

            new_version = DocumentVersion.objects.create(
                document=document,
                file=signed_file,
                file_hash=new_file_hash,
                version_number=new_version_number,
            )

            document.status = "COMPLETED_EXTERNAL"
            document.approved_version = new_version
            document.save()

            create_audit_log(
                document,
                request.user,
                "UPLOAD_SIGNED_FILE",
                {
                    "new_version": new_version_number,
                    "new_hash": new_file_hash,
                    "note": "Upload file đã ký ngoài (EXTERNAL)",
                },
            )

            send_notification_task.delay(document.id, "COMPLETED_EXTERNAL")

        return Response(
            {
                "status": document.status,
                "message": "File đã ký ngoài đã được lưu trữ thành công.",
                "version": new_version_number,
            }
        )

    # 5. Download File Đã duyệt (MANAGER/CHECKER/SENDER - Download)
    @action(detail=True, methods=["get"], url_path="download-approved")
    def download_approved(self, request, pk=None):
        document = get_object_or_404(Document, pk=pk)

        # Phân quyền: Cần có role CHECKER/MANAGER HOẶC là SENDER tạo ra hồ sơ
        if not (
            is_allowed_role(request.user, "SENDER")
            or is_allowed_role(request.user, "CHECKER")
            or is_allowed_role(request.user, "MANAGER")
            or document.created_by == request.user
        ):
            return Response(
                {"detail": "Bạn không có quyền download file này."},
                status=status.HTTP_403_FORBIDDEN,
            )

        approved_version = document.approved_version

        if not approved_version:
            return Response(
                {"detail": "Hồ sơ chưa có phiên bản nào được duyệt."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # BƯỚC BẢO MẬT QUAN TRỌNG: Xác thực Hash trước khi Download
        try:
            file_handle = default_storage.open(approved_version.file.name, "rb")
            re_calculated_hash = calculate_sha256_hash(file_handle)
            file_handle.seek(0)  # Quan trọng: Reset con trỏ file sau khi tính hash

        except Http404:
            create_audit_log(
                document,
                request.user,
                "DOWNLOAD_FAIL",
                {"error": "File không tồn tại trên storage."},
            )
            return Response(
                {"detail": "Lỗi: File gốc không tồn tại trên Server."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except Exception as e:
            create_audit_log(
                document, request.user, "DOWNLOAD_FAIL", {"error": f"Lỗi đọc file: {e}"}
            )
            return Response(
                {"detail": f"Lỗi hệ thống: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if re_calculated_hash != approved_version.file_hash:
            create_audit_log(
                document,
                request.user,
                "HASH_VERIFIED_FAIL",
                {"note": "Lỗi toàn vẹn khi download"},
            )
            return Response(
                {
                    "detail": "Lỗi toàn vẹn dữ liệu: Hash file trên server không khớp. KHÔNG THỂ CUNG CẤP FILE."
                },
                status=status.HTTP_409_CONFLICT,
            )

        create_audit_log(
            document,
            request.user,
            "DOWNLOAD_APPROVED",
            {"version": approved_version.version_number},
        )

        response = FileResponse(file_handle, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'attachment; filename="{document.title}_v{approved_version.version_number}.pdf"'
        )
        return response


# ====================================================================
# III. PUBLIC ENDPOINTS (API Công khai)
# ====================================================================


@api_view(["GET"])
def get_public_key(request):
    """API Công khai: Trả về Public Key để xác minh chữ ký nội bộ."""
    try:
        public_key_pem = get_public_key_pem()
        return Response(
            {"public_key_pem": public_key_pem, "algorithm": "RSA/PSS (SHA256)"}
        )
    except ValueError as e:
        return Response(
            {"detail": f"Lỗi cấu hình Public Key: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
def verify_internal_signature(request):
    """API Công khai: Xác minh chữ ký nội bộ của Hệ thống."""
    hash_to_verify = request.data.get("hash_to_verify")
    signature_base64 = request.data.get("signature")

    try:
        public_key_pem = get_public_key_pem()
    except ValueError as e:
        return Response(
            {"detail": f"Lỗi cấu hình Public Key: {e}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    if not hash_to_verify or not signature_base64:
        return Response(
            {"detail": "Thiếu hash hoặc chữ ký."}, status=status.HTTP_400_BAD_REQUEST
        )

    is_valid = verify_data_hash(hash_to_verify, signature_base64, public_key_pem)

    return Response(
        {
            "verified": is_valid,
            "message": "Chữ ký hợp lệ." if is_valid else "Chữ ký không hợp lệ.",
        }
    )
