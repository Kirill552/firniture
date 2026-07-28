from fastapi import APIRouter

from api.schemas import FeaturesResponse
from api.settings import settings

router = APIRouter(tags=["Features"])

@router.get("/features", response_model=FeaturesResponse)
async def get_features() -> FeaturesResponse:
    """Получить статус доступных экспериментальных функций (feature flags)."""
    return FeaturesResponse(
        machine_features_enabled=settings.MVP_MACHINE_FEATURES_ENABLED,
        factory_features_enabled=settings.FACTORY_FEATURES_ENABLED,
    )
