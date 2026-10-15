from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.api.images import router as images_router
from backend.api.audio import router as audio_router
from backend.api.settings import router as settings_router
from backend.api.projects import router as projects_router
from backend.api.storyboards import router as storyboards_router
from backend.config import get_frontend_origins

SERVICE_NAME = "render-video-api"
SERVICE_VERSION = "0.1.0"


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["render-video-api"]
    version: str


def create_app() -> FastAPI:
    application = FastAPI(
        title="RenderVideo API",
        version=SERVICE_VERSION,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_frontend_origins(),
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @application.get("/health", response_model=HealthResponse, tags=["system"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=SERVICE_NAME,
            version=SERVICE_VERSION,
        )

    application.include_router(audio_router)
    application.include_router(images_router)
    application.include_router(settings_router)
    application.include_router(storyboards_router)
    application.include_router(projects_router)

    return application


app = create_app()
