from fastapi import APIRouter

from . import utils, views

router = APIRouter()
router.include_router(utils.router)
router.include_router(views.router)
