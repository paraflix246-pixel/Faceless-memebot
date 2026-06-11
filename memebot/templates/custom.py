"""Custom background template discovery and rendering."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image, ImageDraw

from memebot.config import TEMPLATES_DIR
from memebot.generator.fonts import load_font
from memebot.generator.renderer import HEIGHT, WIDTH, COLORS, _draw_centered_text

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def discover_custom_templates(templates_dir: Path | None = None) -> dict[str, Path]:
    """Auto-discover custom templates from assets/templates/."""
    root = templates_dir or TEMPLATES_DIR
    if not root.exists():
        return {}

    templates: dict[str, Path] = {}
    for path in sorted(root.iterdir()):
        if path.suffix.lower() in IMAGE_EXTENSIONS and path.is_file():
            name = f"custom_{path.stem.lower().replace(' ', '_')}"
            templates[name] = path
            logger.debug("Discovered custom template: %s -> %s", name, path.name)
    return templates


def list_all_templates() -> tuple[list[str], list[tuple[str, Path]]]:
    """Return (builtin_names, custom_name_path_pairs)."""
    from memebot.generator.renderer import RENDERERS

    custom = discover_custom_templates()
    return list(RENDERERS.keys()), list(custom.items())


def render_custom_background(background: Path, captions: list[str]) -> Image.Image:
    """Overlay captions on a custom background image (scaled to 9:16)."""
    bg = Image.open(background).convert("RGB")
    bg = _fit_portrait(bg)

    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Semi-transparent bars for readability
    draw.rectangle((0, 0, WIDTH, 320), fill=(0, 0, 0, 140))
    draw.rectangle((0, HEIGHT - 320, WIDTH, HEIGHT), fill=(0, 0, 0, 140))

    top = captions[0] if captions else "TOP"
    bottom = captions[1] if len(captions) > 1 else "BOTTOM"
    font = load_font(64)

    _draw_centered_text(draw, top, (40, 40, WIDTH - 40, 300), font)
    _draw_centered_text(draw, bottom, (40, HEIGHT - 300, WIDTH - 40, HEIGHT - 40), font)

    bg_rgba = bg.convert("RGBA")
    bg_rgba.alpha_composite(overlay)

    draw_final = ImageDraw.Draw(bg_rgba)
    label = f"Faceless Memebot • {background.stem}"
    draw_final.text((20, HEIGHT - 42), label, fill=COLORS["text_dim"], font=load_font(22))

    return bg_rgba.convert("RGB")


def _fit_portrait(img: Image.Image) -> Image.Image:
    """Crop/scale image to 1080x1920 portrait."""
    target_ratio = WIDTH / HEIGHT
    w, h = img.size
    current_ratio = w / h

    if current_ratio > target_ratio:
        new_w = int(h * target_ratio)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))
    else:
        new_h = int(w / target_ratio)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))

    return img.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
