from fastapi import APIRouter

from .api import utils

router = APIRouter()
router.include_router(utils.router)
