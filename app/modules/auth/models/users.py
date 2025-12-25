from datetime import datetime
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from pydantic import field_validator
from sqlalchemy import Column, DateTime, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel

from ....models.mixins import TimestampMixin
from .roles import UserRole, UserRoleAssociation

if TYPE_CHECKING:
    from .roles import Role, RoleRead

DEPARTMENTS = ["BOD", "ACC", "HR", "LEASING", "MKT", "COM", "IT", "ME", "MO"]


# --- Schemas (Pydantic models) ---

# Shared properties for User models.
class UserBase(SQLModel):
    email: str = Field(index=True, unique=True, nullable=False)
    full_name: Optional[str] = None
    picture_url: Optional[str] = None


# Properties to receive via API on creation (internal use).
class UserCreateInternal(UserBase):
    google_sub: str
    is_active: bool = False


# Properties to receive via API on update status.
class UserUpdateStatus(SQLModel):
    is_active: bool


# Properties to receive via API on update role.
class UserUpdateRole(SQLModel):
    role_name: UserRole


# Properties to receive via API on update profile.
class UserUpdateProfile(SQLModel):
    full_name: Optional[str] = None
    department: Optional[str] = None
    contact_email: Optional[str] = None

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: Optional[str]):
        if v is None: return v
        if v not in DEPARTMENTS:
            raise ValueError(f"Phòng ban '{v}' không hợp lệ. Vui lòng chọn trong danh sách: {', '.join(DEPARTMENTS)}")

        return v

    @field_validator("contact_email")
    @classmethod
    def lower_email(cls, v: Optional[str]) -> Optional[str]:
        if v: return v.lower().strip()

        return v


# Properties to return via API.
class UserRead(UserBase, TimestampMixin):
    """
    User response schema. Requires eager loading for 'roles'.
    """
    id: UUID
    is_active: bool
    google_sub: str
    last_login_at: Optional[datetime] = None

    roles: List["RoleRead"] = []


# --- Table (Database Model) ---

class User(TimestampMixin, UserBase, table=True):
    """
    Database model for users.
    """
    __tablename__ = "users"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, index=True),
    )

    # Google Subject ID (Immutable unique identifier from Google)
    google_sub: str = Field(
        sa_column=Column(String, unique=True, index=True, nullable=False),
    )

    # Onboarding/Profile fields
    contact_email: Optional[str] = Field(
        default=None,
        sa_column=Column(String, unique=True, index=True, nullable=True),
    )

    department: Optional[str] = Field(default=None)

    last_login_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    is_active: bool = Field(default=False)

    # documents: List["Document"] = Relationship(back_populates="creator")
    roles: List["Role"] = Relationship(
        back_populates="users",
        link_model=UserRoleAssociation,
    )
