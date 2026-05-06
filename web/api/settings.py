from fastapi import APIRouter, HTTPException
from services.config_service import ConfigService, SettingsUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])
config_service = ConfigService()

@router.get("")
async def get_settings():
    return config_service.get_settings()

@router.post("")
async def update_settings(settings: SettingsUpdate):
    return config_service.update_settings(settings)
