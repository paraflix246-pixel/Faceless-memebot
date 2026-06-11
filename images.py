"""Stage 3: Scene image generation (SD local / Replicate / DALL-E / placeholders)."""

from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from PIL import Image, ImageDraw, ImageFont

from pipeline_log import log_error, log_info, record_fallback
from scenes import Scene

if TYPE_CHECKING:
    from content_types.base import BaseContentType

OUTPUT_SIZE = (768, 1344)  # portrait SD size, scaled to 1080x1920 in compose


def generate_scene_images(
    scenes: list[Scene],
    content_type: "BaseContentType",
    work_dir: Path,
) -> list[Path]:
    """Generate one image per scene; fall back to colored placeholders."""
    work_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    colors = content_type.placeholder_colors()

    for i, scene in enumerate(scenes):
        out = work_dir / f"scene_{scene.id:02d}.png"
        generated = (
            _try_local_sd(scene.image_prompt, out)
            or _try_replicate(scene.image_prompt, out)
            or _try_dalle(scene.image_prompt, out)
        )
        if generated:
            paths.append(out)
            log_info("images", f"Generated scene {scene.id} via {generated}")
        else:
            record_fallback("placeholder_images")
            color = colors[i % len(colors)]
            _make_placeholder(out, scene, color)
            paths.append(out)
            log_info("images", f"Placeholder for scene {scene.id}")

    return paths


def _try_local_sd(prompt: str, out: Path) -> str | None:
    url = os.getenv("SD_LOCAL_URL", "http://127.0.0.1:7860")
    if os.getenv("SD_LOCAL_ENABLED", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        payload = {
            "prompt": prompt,
            "negative_prompt": "text, watermark, blurry, low quality",
            "width": OUTPUT_SIZE[0],
            "height": OUTPUT_SIZE[1],
            "steps": 20,
        }
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(f"{url.rstrip('/')}/sdapi/v1/txt2img", json=payload)
            resp.raise_for_status()
            import base64

            b64 = resp.json()["images"][0]
            img = Image.open(BytesIO(base64.b64decode(b64)))
            img.save(out)
            return "local_sd"
    except Exception as exc:
        log_error("images", "Local Stable Diffusion failed", exc)
        return None


def _try_replicate(prompt: str, out: Path) -> str | None:
    api_key = os.getenv("REPLICATE_API_KEY")
    if not api_key:
        return None
    try:
        import replicate

        model = os.getenv(
            "REPLICATE_MODEL",
            "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89fbf45f8563961995bd1e021954279dd967832d",
        )
        output = replicate.run(
            model,
            input={
                "prompt": prompt,
                "width": OUTPUT_SIZE[0],
                "height": OUTPUT_SIZE[1],
            },
        )
        url = output[0] if isinstance(output, list) else str(output)
        with httpx.Client(timeout=120.0) as client:
            resp = client.get(url)
            resp.raise_for_status()
            Image.open(BytesIO(resp.content)).save(out)
        return "replicate"
    except Exception as exc:
        log_error("images", "Replicate image gen failed", exc)
        return None


def _try_dalle(prompt: str, out: Path) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or os.getenv("DALLE_ENABLED", "").lower() not in ("1", "true", "yes"):
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.images.generate(
            model=os.getenv("DALLE_MODEL", "dall-e-3"),
            prompt=prompt[:1000],
            size="1024x1792",
            quality="standard",
            n=1,
        )
        url = response.data[0].url
        with httpx.Client(timeout=60.0) as http:
            resp = http.get(url)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
            img.save(out)
        return "dalle"
    except Exception as exc:
        log_error("images", "DALL-E image gen failed", exc)
        return None


def _make_placeholder(out: Path, scene: Scene, color: tuple[int, int, int]) -> None:
    img = Image.new("RGB", OUTPUT_SIZE, color)
    draw = ImageDraw.Draw(img)
    text = scene.narration[:120]
    if len(scene.narration) > 120:
        text += "..."
    font = _load_font(28)
    _draw_wrapped_text(draw, text, font, OUTPUT_SIZE)
    img.save(out)


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/segoeui.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    size: tuple[int, int],
) -> None:
    margin = 40
    max_width = size[0] - 2 * margin
    words = text.split()
    lines: list[str] = []
    current: list[str] = []
    for word in words:
        test = " ".join(current + [word])
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    line_height = draw.textbbox((0, 0), "Ay", font=font)[3] + 8
    total_h = len(lines) * line_height
    y = (size[1] - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (size[0] - w) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += line_height
