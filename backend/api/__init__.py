from fastapi import APIRouter

from backend.api.schedules import router as schedules_router

router = APIRouter()
router.include_router(schedules_router, prefix="/schedules", tags=["schedules"])
