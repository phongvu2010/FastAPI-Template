from django.db import models
from django.conf import settings # Import settings để lấy AUTH_USER_MODEL
from django.contrib.auth.models import AbstractUser

# Lấy User Model đã tùy chỉnh từ settings (Best Practice)
User = settings.AUTH_USER_MODEL

# --- 2. DOCUMENT MANAGEMENT MODELS ---

class DocumentVersion(models.Model):
    # Sử dụng 'documents/%Y/%m/%d/' để tổ chức file tự động theo ngày
    file = models.FileField(upload_to="documents/%Y/%m/%d/")  # Lưu vào mediafiles
    file_hash = models.CharField(max_length=64, unique=True, verbose_name="Hash SHA-256")

    version_number = models.PositiveIntegerField(default=1)
    # Thêm FK đến Document sau khi Document được định nghĩa
    document = models.ForeignKey('Document', on_delete=models.CASCADE, related_name='versions') 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Đảm bảo một Document chỉ có một phiên bản duy nhất với 1 số phiên bản
        unique_together = ('document', 'version_number')


class Document(models.Model):
    STATUS_CHOICES = (
        ("PENDING", "Pending Submission"),
        ("APPROVED_FOR_SIGNING", "Approved for Signing"),
        ("REJECTED", "Rejected"),
        ("COMPLETED_INTERNAL", "Completed Internal Signing"),
        ("COMPLETED_EXTERNAL", "Completed External Signing"),
    )
    title = models.CharField(max_length=255)
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default="PENDING"
    )  #
    approved_version = models.ForeignKey(
        DocumentVersion,
        on_delete=models.SET_NULL,
        null=True,
        related_name="approved_for_doc",
    )  # Phiên bản đã khóa
    internal_signature = models.TextField(blank=True, null=True)  # Chữ ký NB RSA/PSS
    created_by = models.ForeignKey(User, on_delete=models.PROTECT)








    
    
    
        


# Bạn cần đảm bảo đã tạo model AuditLog trong ứng dụng 'audit' hoặc 'documents'
# (giả định đã có để các serializer và utils hoạt động)


# class DocumentStatus(models.TextChoices):
#     """
#     Trạng thái của hồ sơ theo Quy trình Nghiệp vụ (Blueprint).
#     """
#     PENDING = 'PENDING', 'Chờ kiểm tra/duyệt'
#     APPROVED_FOR_SIGNING = 'APPROVED_FOR_SIGNING', 'Đã duyệt, chờ ký chính'
#     REJECTED = 'REJECTED', 'Đã bị từ chối'
#     COMPLETED_INTERNAL = 'COMPLETED_INTERNAL', 'Đã ký chính nội bộ'
#     COMPLETED_EXTERNAL = 'COMPLETED_EXTERNAL', 'Đã ký chính ngoài hệ thống'


# class DocumentVersion(models.Model):
#     """
#     Quản lý phiên bản vật lý và tính toàn vẹn của File PDF.
#     """
#     document = models.ForeignKey(
#         'Document', 
#         on_delete=models.CASCADE, 
#         related_name='versions',
#         verbose_name='Hồ sơ gốc'
#     )
    
#     file = models.FileField(
# #         upload_to='documents/%Y/%m/%d/', 
#         upload_to=get_document_upload_path, 
#         verbose_name='File PDF vật lý'
#     )

#     file_hash = models.CharField(
#         max_length=64, # SHA-256 là 64 ký tự
#         unique=True,
#         db_index=True, # Đánh index để tra cứu nhanh hơn
#         verbose_name='Hash SHA-256',
#         help_text='Giá trị hash duy nhất của file để đảm bảo tính toàn vẹn.'
#     )
    
#     version_number = models.PositiveIntegerField(
#         validators=[MinValueValidator(1)],
#         verbose_name='Số phiên bản'
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name = 'Phiên bản Hồ sơ'
#         verbose_name_plural = 'Các phiên bản Hồ sơ'
#         # Đảm bảo chỉ có một phiên bản duy nhất cho mỗi Document
#         unique_together = ('document', 'version_number')
#         ordering = ['-version_number']
        
#     def __str__(self):
#         return f"{self.document.title} - V{self.version_number}"

#     def calculate_sha256(self):
#         """Hàm helper để tính SHA-256 từ nội dung file."""
#         if not self.file:
#             return None
            
#         hasher = hashlib.sha256()
#         # Đảm bảo đọc nội dung file từ đầu
#         self.file.seek(0)
#         # Đọc file theo chunks để xử lý file lớn
#         for chunk in self.file.chunks():
#             hasher.update(chunk)
            
#         return hasher.hexdigest()

#     def save(self, *args, **kwargs):
#         # Bắt buộc tính Hash nếu chưa có trước khi lưu
#         if not self.file_hash and self.file:
# #             self.file.seek(0)
# #             self.file_hash = hashlib.sha256(self.file.read()).hexdigest() # [cite: 2]
#             self.file_hash = self.calculate_sha256()
            
#         super().save(*args, **kwargs)


# class Document(models.Model):
#     """
#     Hồ sơ nghiệp vụ tổng, chứa metadata và trạng thái hiện tại.
#     """
#     title = models.CharField(max_length=255, verbose_name='Tiêu đề Hồ sơ')
#     slug = models.SlugField(max_length=255, unique=True, blank=True, null=True, 
#                             help_text="Slug tự động cho URL dễ đọc.")
    
#     sender = models.ForeignKey(
#         User, 
#         on_delete=models.PROTECT, 
#         related_name='submitted_documents',
#         verbose_name='Người nộp'
#     )
    
#     status = models.CharField(
#         max_length=30,
#         choices=DocumentStatus.choices,
#         default=DocumentStatus.PENDING,
#         verbose_name='Trạng thái hiện tại'
#     )
    
#     approved_version = models.ForeignKey(
#         DocumentVersion, # Sử dụng string vì DocumentVersion được định nghĩa sau
#         on_delete=models.PROTECT,
#         null=True,
#         blank=True,
#         related_name='approved_for_document',
#         verbose_name='Phiên bản đã được duyệt/khóa'
#     )
    
#     internal_signature = models.TextField(
#         null=True,
#         blank=True,
#         verbose_name='Chữ ký nội bộ',
#         help_text='Chữ ký RSA/PSS của hệ thống trên file hash đã được duyệt.'
#     )
    
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)

#     class Meta:
#         verbose_name = 'Hồ sơ'
#         verbose_name_plural = 'Hồ sơ'
        
#     def __str__(self):
#         return self.title
        
#     def save(self, *args, **kwargs):
#         # Tạo slug tự động nếu chưa có
#         if not self.slug:
#             self.slug = slugify(self.title)
#         super().save(*args, **kwargs)


# def get_document_upload_path(instance, filename):
#     """Tạo đường dẫn upload theo ID tài liệu và số phiên bản."""
#     # Định dạng: documents/doc_<id>/v_<version>/<filename>
#     return f'documents/doc_{instance.document.id}/v_{instance.version_number}/{filename}'

