"""Stage 3: Scene image generation (SD / Replicate / DALL-E / Pollinations / Pillow)."""

from __future__ import annotations

import math
import os
import random
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import quote

import httpx
from PIL import Image, ImageDraw, ImageFont

from pipeline_log import log_error, log_info, record_fallback
from scenes import Scene

if TYPE_CHECKING:
    from content_types.base import BaseContentType

OUTPUT_SIZE = (768, 1344)  # portrait SD size, scaled to 1080x1920 in compose

# Distinct anime-style gradient palettes per scene index
_SCENE_PALETTES: list[tuple[tuple[int, int, int], tuple[int, int, int]]] = [
    ((255, 90, 130), (80, 40, 120)),
    ((60, 140, 255), (20, 30, 80)),
    ((255, 180, 60), (180, 60, 40)),
    ((160, 80, 255), (40, 20, 80)),
    ((80, 220, 180), (20, 80, 100)),
    ((255, 120, 80), (120, 30, 60)),
    ((100, 200, 255), (30, 60, 120)),
    ((255, 100, 200), (80, 20, 100)),
]

_SCENE_ICONS = ("⚡", "🔥", "✨", "🌙", "⭐", "💫", "🌸", "🎭")


def generate_scene_images(
    scenes: list[Scene],
    content_type: "BaseContentType",
    work_dir: Path,
) -> list[Path]:
    """Generate one image per scene with tiered fallbacks."""
    work_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    colors = content_type.placeholder_colors()
    pollinations_enabled = os.getenv("POLLINATIONS_ENABLED", "true").lower() in (
        "1",
        "true",
        "yes",
    )

    for i, scene in enumerate(scenes):
        out = work_dir / f"scene_{scene.id:02d}.png"
        generated = (
            _try_local_sd(scene.image_prompt, out)
            or _try_replicate(scene.image_prompt, out)
            or _try_dalle(scene.image_prompt, out)
            or (_try_pollinations(scene.image_prompt, out) if pollinations_enabled else None)
        )
        if generated:
            paths.append(out)
            log_info("images", f"Generated scene {scene.id} via {generated}")
        else:
            record_fallback("pillow_scene_images")
            color = colors[i % len(colors)]
            _make_rich_scene_image(out, scene, i, color)
            paths.append(out)
            log_info("images", f"Pillow render for scene {scene.id}")

    return paths


def _try_pollinations(prompt: str, out: Path) -> str | None:
    """Free AI image generation via Pollinations.ai (no API key)."""
    try:
        full_prompt = f"{prompt}, anime style, vibrant, no text, vertical composition"
        encoded = quote(full_prompt[:800], safe="")
        url = (
            f"https://image.pollinations.ai/prompt/{encoded}"
            f"?width={OUTPUT_SIZE[0]}&height={OUTPUT_SIZE[1]}&nologo=true"
        )
        timeout = float(os.getenv("POLLINATIONS_TIMEOUT", "90"))
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            if "image" not in content_type and len(resp.content) < 1000:
                return None
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            if img.size != OUTPUT_SIZE:
                img = img.resize(OUTPUT_SIZE, Image.Resampling.LANCZOS)
            img.save(out)
            return "pollinations"
    except Exception as exc:
        log_error("images", "Pollinations image gen failed", exc)
        return None


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


def _make_rich_scene_image(
    out: Path,
    scene: Scene,
    index: int,
    accent: tuple[int, int, int],
) -> None:
    """Programmatic anime-style scene card when no AI image API is available."""
    w, h = OUTPUT_SIZE
    top, bottom = _SCENE_PALETTES[index % len(_SCENE_PALETTES)]
    img = Image.new("RGB", OUTPUT_SIZE)
    draw = ImageDraw.Draw(img)
    _draw_vertical_gradient(img, top, bottom)

    rng = random.Random(scene.id * 997 + index)
    _draw_decorative_elements(draw, w, h, index, accent, rng)
    _draw_silhouette(draw, w, h, index, rng)

    title_font = _load_font(36)
    body_font = _load_font(24)
    badge_font = _load_font(20)

    badge = f"Scene {scene.id}"
    _draw_badge(draw, badge, badge_font, w, accent)

    title = _scene_title(scene)
    _draw_title_block(draw, title, title_font, w, h)

    snippet = scene.image_prompt[:100] if scene.image_prompt else scene.narration[:100]
    if len(scene.image_prompt or scene.narration) > 100:
        snippet += "..."
    _draw_prompt_caption(draw, snippet, body_font, w, h)

    icon = _SCENE_ICONS[index % len(_SCENE_ICONS)]
    _draw_icon_overlay(draw, icon, w, h, index)

    img.save(out)


def _draw_vertical_gradient(
    img: Image.Image,
    top: tuple[int, int, int],
    bottom: tuple[int, int, int],
) -> None:
    w, h = img.size
    pixels = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        r = int(top[0] * (1 - t) + bottom[0] * t)
        g = int(top[1] * (1 - t) + bottom[1] * t)
        b = int(top[2] * (1 - t) + bottom[2] * t)
        for x in range(w):
            pixels[x, y] = (r, g, b)


def _draw_decorative_elements(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    index: int,
    accent: tuple[int, int, int],
    rng: random.Random,
) -> None:
    for _ in range(12 + index * 2):
        x = rng.randint(0, w)
        y = rng.randint(0, h // 2)
        r = rng.randint(2, 6)
        alpha_color = tuple(min(255, c + 40) for c in accent)
        draw.ellipse([x - r, y - r, x + r, y + r], fill=alpha_color)

    for i in range(5):
        cx = w * (0.15 + i * 0.17)
        cy = h * 0.12 + (index * 30) % 80
        points = []
        for j in range(5):
            angle = math.pi / 2 + j * 2 * math.pi / 5
            outer = 18 + (index % 3) * 4
            inner = outer // 2
            for radius, offset in ((outer, 0), (inner, math.pi / 5)):
                px = cx + radius * math.cos(angle + offset)
                py = cy + radius * math.sin(angle + offset)
                points.append((px, py))
        if len(points) >= 3:
            draw.polygon(points[:10], fill=(255, 255, 200))


def _draw_silhouette(
    draw: ImageDraw.ImageDraw,
    w: int,
    h: int,
    index: int,
    rng: random.Random,
) -> None:
    """Simple character silhouette — distinct shape per scene."""
    base_y = int(h * 0.55)
    cx = w // 2 + (index - 2) * 30
    dark = (20, 15, 35)

    # Head
    head_r = 55 + (index % 3) * 8
    draw.ellipse([cx - head_r, base_y - head_r * 3, cx + head_r, base_y - head_r], fill=dark)

    # Body
    body_w = 90 + index * 10
    body_h = 180 + (index % 2) * 40
    draw.rounded_rectangle(
        [cx - body_w // 2, base_y - head_r, cx + body_w // 2, base_y + body_h],
        radius=20,
        fill=dark,
    )

    # Arms (pose varies by scene)
    arm_y = base_y - head_r + 20
    if index % 3 == 0:
        draw.line([(cx - body_w // 2, arm_y), (cx - body_w, arm_y - 60)], fill=dark, width=18)
        draw.line([(cx + body_w // 2, arm_y), (cx + body_w, arm_y + 40)], fill=dark, width=18)
    elif index % 3 == 1:
        draw.line([(cx - body_w // 2, arm_y), (cx - body_w - 20, arm_y + 80)], fill=dark, width=18)
        draw.line([(cx + body_w // 2, arm_y), (cx + body_w + 20, arm_y + 80)], fill=dark, width=18)
    else:
        draw.line([(cx - body_w // 2, arm_y), (cx - body_w // 2 - 40, arm_y - 80)], fill=dark, width=18)
        draw.line([(cx + body_w // 2, arm_y), (cx + body_w // 2 + 40, arm_y - 80)], fill=dark, width=18)

    # Ground glow
    glow_w = 200 + index * 20
    draw.ellipse(
        [cx - glow_w, base_y + body_h - 20, cx + glow_w, base_y + body_h + 40],
        fill=(255, 255, 255, 30) if hasattr(draw, "ellipse") else (60, 50, 80),
    )


def _draw_badge(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    w: int,
    accent: tuple[int, int, int],
) -> None:
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 16, 8
    x = (w - tw) // 2 - pad_x
    y = 36
    draw.rounded_rectangle(
        [x, y, x + tw + 2 * pad_x, y + th + 2 * pad_y],
        radius=12,
        fill=accent,
    )
    draw.text((x + pad_x, y + pad_y), text, fill=(255, 255, 255), font=font)


def _draw_title_block(
    draw: ImageDraw.ImageDraw,
    title: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    w: int,
    h: int,
) -> None:
    lines = _wrap_text(draw, title, font, w - 80)
    line_h = draw.textbbox((0, 0), "Ay", font=font)[3] + 10
    total_h = len(lines) * line_h
    y = h - 280 - total_h
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0), font=font)
        draw.text((x, y), line, fill=(255, 255, 255), font=font)
        y += line_h


def _draw_prompt_caption(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    w: int,
    h: int,
) -> None:
    lines = _wrap_text(draw, text, font, w - 100)[:2]
    y = h - 120
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        tw = bbox[2] - bbox[0]
        x = (w - tw) // 2
        draw.text((x, y), line, fill=(220, 220, 240), font=font)
        y += draw.textbbox((0, 0), "Ay", font=font)[3] + 6


def _draw_icon_overlay(
    draw: ImageDraw.ImageDraw,
    icon: str,
    w: int,
    h: int,
    index: int,
) -> None:
    font = _load_font(72)
    x = w - 100 if index % 2 == 0 else 40
    y = int(h * 0.28)
    draw.text((x + 2, y + 2), icon, fill=(0, 0, 0), font=font)
    draw.text((x, y), icon, fill=(255, 255, 255), font=font)


def _scene_title(scene: Scene) -> str:
    words = scene.narration.split()
    if len(words) <= 8:
        return scene.narration
    return " ".join(words[:8]) + "..."


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
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
    return lines


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()
