import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.engine import Connection
from sqlmodel import Session
from typing import Sequence

from app.db.database import engine
from app.modules.users.models import RoleCreate, UserRole, Role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DEFAULT_ROLES: Sequence[RoleCreate] = [
    RoleCreate(
        name=UserRole.ADMIN,
        description="Quản trị viên toàn hệ thống, có quyền cao nhất.",
    ),
    RoleCreate(
        name=UserRole.MANAGER,
        description="Quản lý, có quyền phê duyệt, quản lý người dùng và tài liệu.",
    ),
    RoleCreate(
        name=UserRole.CHECKER,
        description="Người kiểm tra, có quyền kiểm tra và phê duyệt tài liệu.",
    ),
    RoleCreate(
        name=UserRole.SENDER,
        description="Người gửi, có quyền tạo và gửi tài liệu.",
    ),
]


def create_default_roles(conn: Connection) -> None:
    """
    Sync function to seed default roles.
    """
    with Session(conn) as session:
        for role_data in DEFAULT_ROLES:
            statement = select(Role).where(Role.name == role_data.name)
            existing_role = session.exec(statement).first()

            if not existing_role:
                role = Role.model_validate(role_data)
                session.add(role)
                logger.info(f" Created default role: {role.name.value}")
            else:
                logger.info(f" Role already exists: {role_data.name.value}")

        session.commit()


async def init_db() -> None:
    """
    Initializes the database and seeds default data.
    """
    logger.info(" Initializing database...")
    async with engine.begin() as conn:
        await conn.run_sync(create_default_roles)
    logger.info(" Database initialization completed.")


if __name__ == "__main__":
    asyncio.run(init_db())
