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
