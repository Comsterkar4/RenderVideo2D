from fastapi import APIRouter, HTTPException, status

from backend.providers.speech.vivibe import (
    VIVIBE_KEY_STORE,
    configured_vivibe_api_key,
    vivibe_key_source,
)
from backend.schemas import VivibeKeyStatus, VivibeKeyUpdate

router = APIRouter(prefix="/api/settings", tags=["settings"])


def current_vivibe_key_status() -> VivibeKeyStatus:
    source = vivibe_key_source()
    return VivibeKeyStatus(
        configured=configured_vivibe_api_key() is not None,
        source=source,
        volatile=source == "web",
    )


@router.get("/vivibe-key", response_model=VivibeKeyStatus)
def get_vivibe_key() -> VivibeKeyStatus:
    return current_vivibe_key_status()


@router.put("/vivibe-key", response_model=VivibeKeyStatus)
def replace_vivibe_key(settings: VivibeKeyUpdate) -> VivibeKeyStatus:
    try:
        VIVIBE_KEY_STORE.replace(settings.key.get_secret_value())
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return current_vivibe_key_status()


@router.delete("/vivibe-key", response_model=VivibeKeyStatus)
def clear_vivibe_key() -> VivibeKeyStatus:
    VIVIBE_KEY_STORE.clear()
    return current_vivibe_key_status()
