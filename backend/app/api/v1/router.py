from fastapi import APIRouter

from app.api.v1.achievements import router as achievements_router
from app.api.v1.admin import router as admin_router
from app.api.v1.ai import router as ai_router
from app.api.v1.applications import router as applications_router
from app.api.v1.auth import router as auth_router
from app.api.v1.evaluations import router as evaluations_router
from app.api.v1.health import router as health_router
from app.api.v1.scholarships import router as scholarships_router
from app.api.v1.stages import router as stages_router
from app.api.v1.templates import router as templates_router
from app.api.v1.users import router as users_router


api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(health_router)
api_router.include_router(users_router)
api_router.include_router(scholarships_router)
api_router.include_router(stages_router)
api_router.include_router(templates_router)
api_router.include_router(applications_router)
api_router.include_router(evaluations_router)
api_router.include_router(achievements_router)
api_router.include_router(ai_router)
api_router.include_router(admin_router)
