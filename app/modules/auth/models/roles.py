from enum import Enum
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, Enum as SQLAlchemyEnum, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship

from ....core.db import Base

if TYPE_CHECKING:
    from .users import User


class UserRole(str, Enum):
    """
    Enumeration of system user roles.
    """
    SENDER = "SENDER"
    CHECKER = "CHECKER"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class UserRoleAssociation(Base, table=True):
    """
    Many-to-Many association table between Users and Roles.
    """
    __tablename__ = "user_role_association"
    __table_args__ = (
        Index("ix_user_role_user_id", "user_id"),
        Index("ix_user_role_role_id", "role_id"),
    )

    user_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    role_id: UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )


# --- Schemas (Pydantic models) ---

# Shared properties for Role models.
class RoleBase(Base):
    name: UserRole = Field(index=True, unique=True)
    description: Optional[str] = None


# Properties to receive via API on creation.
class RoleCreate(RoleBase):
    pass


# Properties to return via API.
class RoleRead(RoleBase):
    id: UUID


# --- Table (Database Model) ---

class Role(RoleBase, table=True):
    """
    Database model for roles.
    """
    __tablename__ = "roles"

    id: UUID = Field(
        default_factory=uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True, index=True),
    )

    # Explicit SQLAlchemy Enum required for Postgres strict handling
    name: UserRole = Field(
        sa_column=Column(
            SQLAlchemyEnum(UserRole, name="user_role_enum", create_constraint=False),
            unique=True,
            nullable=False,
        ),
    )

    users: List["User"] = Relationship(
        back_populates="roles",
        link_model=UserRoleAssociation,
    )
