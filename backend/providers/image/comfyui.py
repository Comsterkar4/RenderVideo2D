import json
import os
import time
from typing import Any
from uuid import uuid4

import httpx

from backend.config import PROJECT_ROOT
from backend.providers.image.base import (
    GeneratedImage,
    ImageGenerationRequest,
    ImageProviderError,
    ImageProviderResponseError,
    ImageProviderUnavailableError,
)


class ComfyUIProviderError(ImageProviderError):
    pass


class ComfyUIUnavailableError(ComfyUIProviderError, ImageProviderUnavailableError):
    pass


class ComfyUIResponseError(ComfyUIProviderError, ImageProviderResponseError):
    pass


class ComfyUIImageProvider:
    name = "comfyui"
    uses_local_gpu = True

    def __init__(
        self,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        self.base_url = (
            base_url or os.getenv("COMFYUI_BASE_URL", "http://127.0.0.1:8188")
        ).rstrip("/")
        self.timeout_seconds = timeout_seconds or float(
            os.getenv("COMFYUI_IMAGE_TIMEOUT_SECONDS", "1800")
        )
        self.model = os.getenv(
            "COMFYUI_CHECKPOINT",
            "dreamshaper_8.safetensors",
        )

    def device_type(self) -> str:
        timeout = httpx.Timeout(connect=10, read=30, write=10, pool=10)
        try:
            with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                response = client.get("/system_stats")
                response.raise_for_status()
                devices = response.json().get("devices", [])
                return str(devices[0].get("type", "unknown")) if devices else "unknown"
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyUIUnavailableError(
                f"Cannot connect to ComfyUI at {self.base_url}"
            ) from exc
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise ComfyUIResponseError("ComfyUI returned invalid system stats") from exc

    def generate(self, request: ImageGenerationRequest) -> GeneratedImage:
        device_type = self.device_type()
        cpu_mode = device_type == "cpu"
        width, height = image_dimensions(request.aspect_ratio, cpu_mode=cpu_mode)
        steps = 12 if cpu_mode else 24
        workflow = build_workflow(
            prompt=request.prompt,
            negative_prompt=request.negative_prompt,
            seed=request.seed,
            steps=steps,
            width=width,
            height=height,
            checkpoint=self.model,
            filename_prefix=request.filename_prefix,
        )
        timeout = httpx.Timeout(connect=10, read=30, write=30, pool=10)
        try:
            with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                prompt_id = self._queue_prompt(client, workflow)
                image = self._wait_for_image(client, prompt_id)
                response = client.get(
                    "/view",
                    params={
                        "filename": image["filename"],
                        "subfolder": image.get("subfolder", ""),
                        "type": image.get("type", "output"),
                    },
                )
                response.raise_for_status()
                return GeneratedImage(
                    content=response.content,
                    media_type="image/png",
                    file_extension=".png",
                    external_job_id=prompt_id,
                    metadata={
                        "width": width,
                        "height": height,
                        "steps": steps,
                        "device_type": device_type,
                        "checkpoint": self.model,
                        "workflow": "scene-image.v1",
                        "comfyui_output": {
                            "filename": image["filename"],
                            "subfolder": image.get("subfolder", ""),
                            "type": image.get("type", "output"),
                        },
                    },
                )
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyUIUnavailableError(
                f"Cannot connect to ComfyUI at {self.base_url}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ComfyUIUnavailableError("ComfyUI request timed out") from exc
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text[:500]
            raise ComfyUIResponseError(
                f"ComfyUI returned HTTP {exc.response.status_code}: {detail}"
            ) from exc

    def release(self) -> None:
        timeout = httpx.Timeout(connect=10, read=30, write=30, pool=10)
        try:
            with httpx.Client(base_url=self.base_url, timeout=timeout) as client:
                response = client.post(
                    "/free",
                    json={"unload_models": True, "free_memory": True},
                )
                response.raise_for_status()
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise ComfyUIUnavailableError(
                f"Cannot connect to ComfyUI at {self.base_url}"
            ) from exc
        except httpx.HTTPError as exc:
            raise ComfyUIResponseError("ComfyUI could not release model memory") from exc

    def _queue_prompt(self, client: httpx.Client, workflow: dict[str, Any]) -> str:
        response = client.post(
            "/prompt",
            json={"prompt": workflow, "client_id": str(uuid4())},
        )
        response.raise_for_status()
        try:
            return str(response.json()["prompt_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ComfyUIResponseError("ComfyUI did not return a prompt_id") from exc

    def _wait_for_image(self, client: httpx.Client, prompt_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout_seconds
        while time.monotonic() < deadline:
            response = client.get(f"/history/{prompt_id}")
            response.raise_for_status()
            history = response.json().get(prompt_id)
            if history is None:
                time.sleep(1)
                continue

            status = history.get("status", {})
            if status.get("status_str") == "error":
                raise ComfyUIResponseError(self._execution_error(status))

            for output in history.get("outputs", {}).values():
                images = output.get("images", [])
                if images:
                    return images[0]

            if status.get("completed"):
                raise ComfyUIResponseError("ComfyUI completed without an image output")
            time.sleep(1)

        raise ComfyUIUnavailableError(
            f"ComfyUI did not finish within {self.timeout_seconds:g} seconds"
        )

    @staticmethod
    def _execution_error(status: dict[str, Any]) -> str:
        for message in reversed(status.get("messages", [])):
            if isinstance(message, list) and message and message[0] == "execution_error":
                detail = message[1] if len(message) > 1 else {}
                return f"ComfyUI execution failed: {detail.get('exception_message', 'unknown error')}"
        return "ComfyUI execution failed"


WORKFLOW_PATH = PROJECT_ROOT / "workflows" / "scene-image.v1.json"


def build_workflow(
    *,
    prompt: str,
    negative_prompt: str,
    seed: int,
    steps: int,
    width: int,
    height: int,
    checkpoint: str,
    filename_prefix: str,
) -> dict[str, Any]:
    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = steps
    workflow["4"]["inputs"]["ckpt_name"] = checkpoint
    workflow["5"]["inputs"]["width"] = width
    workflow["5"]["inputs"]["height"] = height
    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = negative_prompt
    workflow["9"]["inputs"]["filename_prefix"] = filename_prefix
    return workflow


def image_dimensions(aspect_ratio: str, *, cpu_mode: bool) -> tuple[int, int]:
    if cpu_mode:
        return {
            "9:16": (384, 576),
            "16:9": (576, 384),
            "1:1": (448, 448),
        }[aspect_ratio]
    return {
        "9:16": (512, 768),
        "16:9": (768, 512),
        "1:1": (512, 512),
    }[aspect_ratio]

