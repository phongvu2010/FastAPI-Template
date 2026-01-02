from rest_framework import serializers
from .models import Document, DocumentVersion
from accounts.models import User

class UserSimpleSerializer(serializers.ModelSerializer):
    """Serializer đơn giản cho thông tin người dùng."""
    class Meta:
        model = User
        fields = ['id', 'email', 'first_name', 'last_name', 'role']

class DocumentVersionSerializer(serializers.ModelSerializer):
    """Serializer cho phiên bản tài liệu."""
    uploaded_by = UserSimpleSerializer(read_only=True)

    class Meta:
        model = DocumentVersion
        fields = [
            'id', 'document', 'uploaded_by', 'uploaded_at',
            'file', 'file_hash', 'version_number', 'notes'
        ]
        read_only_fields = [
            'document', 'uploaded_by', 'file_hash', 'version_number'
        ]

class DocumentDetailSerializer(serializers.ModelSerializer):
    """Serializer chi tiết cho Document, bao gồm các phiên bản."""
    creator = UserSimpleSerializer(read_only=True)
    versions = DocumentVersionSerializer(many=True, read_only=True)
    approved_version = DocumentVersionSerializer(read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'creator', 'created_at', 'status',
            'approved_version', 'metadata', 'versions'
        ]

class DocumentCreateSerializer(serializers.ModelSerializer):
    """Serializer riêng cho việc Upload/Tạo mới Document."""
    file = serializers.FileField(write_only=True, required=True)
    notes = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Document
        fields = ['id', 'title', 'metadata', 'file', 'notes']

class RejectSerializer(serializers.Serializer):
    """Serializer cho hành động Reject, yêu cầu lý do."""
    reason = serializers.CharField(required=True, max_length=1024)

class ExternalSignedUploadSerializer(serializers.Serializer):
    """
    Serializer cho việc upload file đã được ký bởi bên ngoài.
    """
    signed_file = serializers.FileField(required=True)
    # File chứa chứng thư (ví dụ: .cer) hoặc chuỗi chứng thư PEM/DER
    certificate = serializers.CharField(required=False, allow_blank=True, max_length=4096)
    # Thông tin bổ sung (ví dụ: Tên dịch vụ ký số, ID giao dịch)
    meta = serializers.JSONField(required=False, default=dict)
