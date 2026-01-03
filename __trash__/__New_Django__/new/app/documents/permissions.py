from rest_framework import permissions

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "ADMIN"

class IsSender(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "SENDER"

class IsChecker(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "CHECKER"

class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == "MANAGER"

# Các quyền phức hợp (ví dụ: chỉ checker hoặc admin)
class IsCheckerOrAdmin(permissions.BasePermission):
     def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["CHECKER", "ADMIN"]

class IsManagerOrAdmin(permissions.BasePermission):
     def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ["MANAGER", "ADMIN"]
