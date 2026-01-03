"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # Thêm dòng này
    path('api/', include('documents.urls')),

    # (Bạn cũng sẽ cần include 'accounts.urls' và 'allauth.urls' ở đây)
    path('accounts/', include('allauth.urls')),
]




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







# from django.conf import settings
# from django.conf.urls.static import static

from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    # Thêm URL của Allauth
    path("accounts/", include("allauth.urls")),
    # Các URL API của bạn (nếu có)
    # path("api/", include("documents.urls")),
]

# # Thêm cấu hình phục vụ MEDIA files trong môi trường phát triển (DEBUG=True)
# if settings.DEBUG:
#     urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
