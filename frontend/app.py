import os
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

FRONTEND_ROOT = Path(__file__).resolve().parent
API_BASE_URL = os.getenv("BACKEND_PUBLIC_URL", "http://127.0.0.1:9000")

app = FastAPI(
    title="RenderVideo UI",
    version="0.1.0",
    docs_url=None,
    redoc_url=None,
)
app.mount("/static", StaticFiles(directory=FRONTEND_ROOT / "static"), name="static")
templates = Jinja2Templates(directory=FRONTEND_ROOT / "templates")

FAVICON_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
    '<rect width="32" height="32" rx="8" fill="#18211d"/>'
    '<text x="16" y="21" font-size="13" font-weight="800" '
    'font-family="system-ui, sans-serif" fill="#ffffff" text-anchor="middle">RV</text>'
    '</svg>'
)

class FrontendHealth(BaseModel):
    status: Literal["ok"]
    service: Literal["render-video-ui"]
    api_base_url: str


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"api_base_url": API_BASE_URL},
    )

@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.get("/health", response_model=FrontendHealth)
def health() -> FrontendHealth:
    return FrontendHealth(
        status="ok",
        service="render-video-ui",
        api_base_url=API_BASE_URL,
    )
