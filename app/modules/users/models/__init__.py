# Export core models and schemas for easy access throughout the app
from .role import Role, UserRole, UserRoleAssociation, RoleCreate, RoleRead
from .user import (
    User,
    UserCreateInternal,
    UserRead,
    UserUpdateStatus,
    UserUpdateRole,
    UserUpdateProfile,
)


# from sqlmodel import SQLModel

# # Rebuild models to resolve forward references (Circular dependency handling)
# User.model_rebuild()
# Role.model_rebuild()
# UserRead.model_rebuild()
# RoleRead.model_rebuild()

# # Rebuild Document models if they have circular refs with User
# Document.model_rebuild()
# DocumentVersion.model_rebuild()
# Signature.model_rebuild()

# __all__ = [
#     "SQLModel",
#     "User",
#     "UserCreateInternal",
#     "UserUpdateStatus",
#     "UserUpdateRole",
#     "UserUpdateProfile",
#     "UserRead",
#     "Role",
#     "UserRole",
#     "RoleRead",
#     "RoleCreate",
#     "UserRoleAssociation",
#     # Export Documents
#     "Document",
#     "DocumentVersion",
#     "DocumentStatus",
#     "Signature",
#     "AuditLog",
#     "AuditAction",
# ]
