
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView, # Nên có để kiểm tra tính hợp lệ của Token
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- JWT Authentication URLs ---
    path('api/auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'), # Lấy Access và Refresh Token
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'), # Làm mới Access Token
    path('api/auth/token/verify/', TokenVerifyView.as_view(), name='token_verify'), # Kiểm tra Token
    
    path('api/documents/', include('documents.urls')), 
]

# Cấu hình để phục vụ các file media (rất quan trọng cho việc truy cập file)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
