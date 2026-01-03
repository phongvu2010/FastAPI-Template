from rest_framework import serializers
from .models import Document, DocumentVersion

class DocumentUploadSerializer(serializers.Serializer):
    """
    Serializer này được dùng để xử lý dữ liệu đầu vào từ người dùng 
    khi họ tải lên một phiên bản file PDF.
    """
    document_id = serializers.IntegerField(required=False)
    title = serializers.CharField(max_length=255, required=False)
    file = serializers.FileField()
    
    def validate(self, data):
        # Đảm bảo có đủ thông tin khi tạo tài liệu mới
        if 'document_id' not in data and not data.get('title'):
            raise serializers.ValidationError(
                "Phải cung cấp document_id để cập nhật hoặc title để tạo mới."
            )
        return data

class DocumentReviewSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    # Trường tùy chọn cho hành động từ chối
    rejection_reason = serializers.CharField(required=False, allow_blank=True) 

    def validate_document_id(self, value):
        try:
            document = Document.objects.get(pk=value)
        except Document.DoesNotExist:
            raise serializers.ValidationError("Hồ sơ không tồn tại.")
            
        # Kiểm tra trạng thái: Chỉ có thể duyệt/từ chối hồ sơ ở trạng thái PENDING
        if document.status != 'PENDING':
            raise serializers.ValidationError(f"Hồ sơ này đang ở trạng thái '{document.status}' và không thể duyệt hoặc từ chối.")
        
        # Lưu đối tượng document vào context để tái sử dụng trong view
        self.document = document 
        return value

class DocumentSignSerializer(serializers.Serializer):
    document_id = serializers.IntegerField()
    # Thêm trường để chứa chữ ký thực tế (base64, hoặc ID chữ ký nếu dùng HSM)
    signature_data = serializers.CharField(required=True) 

    def validate_document_id(self, value):
        try:
            document = Document.objects.get(pk=value)
        except Document.DoesNotExist:
            raise serializers.ValidationError("Hồ sơ không tồn tại.")
            
        # Kiểm tra trạng thái: Chỉ có thể ký hồ sơ ở trạng thái APPROVED_FOR_SIGNING
        if document.status != 'APPROVED_FOR_SIGNING':
            raise serializers.ValidationError(f"Hồ sơ này đang ở trạng thái '{document.status}' và không thể ký chính thức.")
        
        # Lưu đối tượng document vào context
        self.document = document 
        return value
