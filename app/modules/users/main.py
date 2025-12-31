from fastapi import APIRouter

from ...core.config import settings
from .api import auth, users, views

router = APIRouter()
router.include_router(auth.router, prefix=settings.API_V1_STR)
router.include_router(users.router, prefix=settings.API_V1_STR)
router.include_router(views.router)
