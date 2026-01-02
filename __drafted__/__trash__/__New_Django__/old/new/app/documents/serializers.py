# documents_app/serializers.py

from rest_framework import serializers
from .models import User, Document, DocumentVersion, AuditLog


# ----------------------------------------------------
# 1. User Serializers
# ----------------------------------------------------
class UserSerializer(serializers.ModelSerializer):
    """
    Serializer cho model User.
    Chỉ hiển thị các trường an toàn.
    """

    # Lấy danh sách các lựa chọn ROLE từ model
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES)

    class Meta:
        model = User
        fields = (
            "id",
            "username",  # Tên đăng nhập (nếu không dùng SSO)
            "email",
            "first_name",
            "last_name",
            "role",
            "is_staff",
            "is_active",
            "date_joined",
        )
        read_only_fields = (
            "date_joined",
            "is_staff",
        )  # Các trường không cho phép chỉnh sửa trực tiếp qua API
        extra_kwargs = {
            "email": {"required": True},  # Đảm bảo email luôn được cung cấp
            # Bảo mật: Không bao giờ hiển thị password qua API
            "password": {"write_only": True, "required": False},
        }

    def create(self, validated_data):
        """
        Xử lý việc tạo User mới.
        Sử dụng set_password để đảm bảo mật khẩu được hash.
        """
        password = validated_data.pop("password", None)
        user = User.objects.create(**validated_data)

        if password:
            user.set_password(password)
            user.save()
        return user

    def update(self, instance, validated_data):
        """
        Xử lý việc cập nhật User.
        """
        # Cập nhật các trường khác trước
        for attr, value in validated_data.items():
            if attr == "password":
                # Đảm bảo mật khẩu được hash nếu được cập nhật
                instance.set_password(value)
            else:
                setattr(instance, attr, value)

        instance.save()
        return instance


# ----------------------------------------------------
# 2. Document Serializers (Bổ sung cho hoàn chỉnh)
# ----------------------------------------------------


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.ReadOnlyField(source="actor.email")

    class Meta:
        model = AuditLog
        fields = ("id", "action", "details", "timestamp", "actor_email")


class DocumentVersionSerializer(serializers.ModelSerializer):

    class Meta:
        model = DocumentVersion
        fields = ("id", "version_number", "file", "file_hash", "created_at")
        read_only_fields = ("file_hash", "created_at", "file")


class DocumentSerializer(serializers.ModelSerializer):
    # Lấy thông tin phiên bản đã duyệt (Read-only)
    approved_version_info = DocumentVersionSerializer(
        source="approved_version", read_only=True
    )
    # Lấy log lịch sử (Read-only)
    audit_logs = AuditLogSerializer(source="auditlog_set", many=True, read_only=True)
    created_by_email = serializers.ReadOnlyField(source="created_by.email")

    class Meta:
        model = Document
        # Thêm các trường hiển thị thông tin ký số và trạng thái
        fields = (
            "id",
            "title",
            "status",
            "internal_signature",
            "created_by_email",
            "approved_version",  # FK ID
            "approved_version_info",  # Object chi tiết
            "audit_logs",
        )
        read_only_fields = (
            "status",
            "internal_signature",
            "approved_version",
            "created_by_email",
        )
