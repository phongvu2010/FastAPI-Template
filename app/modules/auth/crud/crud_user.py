from typing import List, Optional
from uuid import UUID

from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import Role, RoleRead, User, UserCreateInternal, UserRole


# --- Role Queries ---

async def get_role_by_name(db: AsyncSession, role_name: UserRole) -> Optional[Role]:
    """
    Retrieves a Role object by its Enum name.
    """
    result = await db.execute(
        select(Role)
        .where(Role.name == role_name)
    )
    return result.scalars().first()


async def get_all_roles(db: AsyncSession) -> List[RoleRead]:
    """
    Retrieves all roles available in the system.
    """
    result = await db.execute(select(Role))
    return result.scalars().all()


# --- User Queries ---

async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> Optional[User]:
    """
    Retrieves a User by their unique Google ID (sub), eager loading roles.
    """
    result = await db.execute(
        select(User)
        .where(User.google_sub == google_sub)
        .options(selectinload(User.roles))
    )
    return result.scalars().first()


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    """
    Retrieves a User by their UUID, eager loading roles.
    """
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(selectinload(User.roles))
    )
    return result.scalars().first()


async def get_all_users(db: AsyncSession) -> List[User]:
    """
    Retrieves all users, including their roles, ordered by email.
    """
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles))
        .order_by(User.email.asc())
    )
    return result.scalars().all()


# --- User Commands ---

async def create_user_from_sso(
    db: AsyncSession,
    user_in: UserCreateInternal,
    initial_role_name: UserRole,
) -> User:
    """
    Creates a new user and assigns an initial role based on SSO data.
    """
    user = User.model_validate(user_in)

    if not user.contact_email:
        user.contact_email = user.email

    initial_role = await get_role_by_name(db, initial_role_name)
    if initial_role:
        user.roles.append(initial_role)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_last_login(db: AsyncSession, user: User) -> User:
    """
    Updates the user's last login timestamp.
    """
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_profile(db: AsyncSession, user: User, update_data: dict) -> User:
    """
    Updates the user's profile.
    """
    for field, value in update_data.items():
        setattr(user, field, value)

    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user_status(db: AsyncSession, user: User, is_active: bool) -> User:
    """
    Updates the user's active/inactive status.
    """
    user.is_active = is_active
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def add_role_to_user(db: AsyncSession, user: User, role: Role) -> User:
    """
    Adds a role to a user if not already present.
    """
    if role not in user.roles:
        user.roles.append(role)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user


async def remove_role_from_user(db: AsyncSession, user: User, role: Role) -> User:
    """
    Removes a role from a user.
    """
    if role in user.roles:
        user.roles.remove(role)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return user
