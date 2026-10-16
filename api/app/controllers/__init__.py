from fastapi import APIRouter

from app.controllers.admin_controller import router as admin_router
from app.controllers.auth_controller import router as auth_router
from app.controllers.health_controller import router as health_router
from app.controllers.level_controller import router as level_router
from app.controllers.match_controller import router as match_router
from app.controllers.progress_controller import router as progress_router
from app.controllers.user_controller import router as user_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(level_router)
api_router.include_router(match_router)
api_router.include_router(progress_router)
api_router.include_router(admin_router)
