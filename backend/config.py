import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VIDEO_LANGUAGE = "vi"
VIDEO_LANGUAGE_NAME = "tiếng Việt"
VISUAL_STYLE = "hoạt hình 2D vẽ tay, màu phẳng, đường nét rõ, thân thiện với trẻ em"
DEFAULT_DATABASE_PATH = PROJECT_ROOT / "data" / "render_video.db"


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DEFAULT_DATABASE_PATH}",
    )


def get_frontend_origins() -> list[str]:
    configured = os.environ.get(
        "FRONTEND_ORIGINS",
        "http://127.0.0.1:9001,http://localhost:9001",
    )
    return [origin.strip() for origin in configured.split(",") if origin.strip()]
