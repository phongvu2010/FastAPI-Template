from fastapi import APIRouter

from .api import auth

from ...core.config import settings
from .api import users

router = APIRouter()
router.include_router(auth.router, prefix=settings.API_V1_STR)
router.include_router(users.router, prefix=settings.API_V1_STR)
