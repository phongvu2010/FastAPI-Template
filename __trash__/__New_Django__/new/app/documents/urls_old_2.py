from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DocumentViewSet,
    UserViewSet,
    get_public_key,
    verify_internal_signature,
)

# Khởi tạo Router (Xử lý các route RESTful)
router = DefaultRouter()
router.register(r"documents", DocumentViewSet, basename="document")
# BỔ SUNG: Định tuyến cho User Management (Chỉ ADMIN)
router.register(r"users", UserViewSet, basename="user")

urlpatterns = [
    # API endpoints cho nghiệp vụ (GET/POST/PUT/DELETE trên /documents/ và /users/)
    path("", include(router.urls)),
    # API Công khai (Không cần xác thực)
    path("public/key/", get_public_key, name="public-key"),  # Route Công bố Public Key
    path(
        "public/verify-signature/", verify_internal_signature, name="verify-signature"
    ),
]
