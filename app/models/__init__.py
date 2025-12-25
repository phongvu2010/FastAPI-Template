# from sqlmodel import SQLModel

# Export core models and schemas for easy access throughout the app
# from ..modules.auth.models import Role, UserRoleAssociation, User

# from ..modules.auth.models import Role, RoleCreate, RoleRead, UserRole, UserRoleAssociation
# from ..modules.auth.models import (
#     User,
#     UserCreateInternal,
#     UserRead,
#     UserUpdateProfile,
#     UserUpdateRole,
#     UserUpdateStatus,
# )

# # Rebuild models to resolve forward references (Circular dependency handling)
# User.model_rebuild()
# Role.model_rebuild()
# UserRead.model_rebuild()
# RoleRead.model_rebuild()

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
# ]
