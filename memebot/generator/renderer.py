"""Pillow-based meme image rendering."""

from __future__ import annotations

import textwrap
from typing import Sequence

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from memebot.generator.fonts import load_font

# Social-friendly 9:16 portrait for Reels/TikTok/Shorts
WIDTH = 1080
HEIGHT = 1920

COLORS = {
    "bg_dark": (18, 18, 24),
    "bg_panel": (32, 32, 42),
    "accent": (255, 69, 96),
    "accent2": (78, 205, 196),
    "text": (255, 255, 255),
    "text_dim": (180, 180, 190),
    "reject": (220, 60, 60),
    "accept": (60, 180, 100),
}


def _new_canvas() -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg_dark"])
    draw = ImageDraw.Draw(img)
    return img, draw


def _gradient_background() -> Image.Image:
    base = Image.new("RGB", (WIDTH, HEIGHT), COLORS["bg_dark"])
    overlay = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(overlay)
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(18 + ratio * 40)
        g = int(18 + ratio * 20)
        b = int(24 + ratio * 60)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    return Image.blend(base, overlay, alpha=0.85)


def _wrap_text(text: str, width: int = 28) -> str:
    return textwrap.fill(text, width=width)


def _draw_centered_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.FreeTypeFont | ImageFont.ImageFont,
    fill: tuple[int, int, int] = COLORS["text"],
    stroke: int = 3,
) -> None:
    wrapped = _wrap_text(text, width=22 if box[2] - box[0] < WIDTH else 28)
    x0, y0, x1, y1 = box
    bbox = draw.multiline_textbbox((0, 0), wrapped, font=font, align="center")
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    x = x0 + (x1 - x0 - tw) // 2
    y = y0 + (y1 - y0 - th) // 2
    draw.multiline_text(
        (x, y),
        wrapped,
        font=font,
        fill=fill,
        align="center",
        stroke_width=stroke,
        stroke_fill=(0, 0, 0),
    )


def _draw_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    fill: tuple[int, int, int],
    radius: int = 20,
) -> None:
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=(60, 60, 70), width=2)


def render_classic(captions: Sequence[str]) -> Image.Image:
    """Classic top/bottom impact-style meme."""
    img = _gradient_background()
    draw = ImageDraw.Draw(img)
    font = load_font(72)
    top = captions[0] if captions else "TOP TEXT"
    bottom = captions[1] if len(captions) > 1 else "BOTTOM TEXT"
    _draw_centered_text(draw, top.upper(), (40, 80, WIDTH - 40, 400), font)
    _draw_centered_text(draw, bottom.upper(), (40, HEIGHT - 420, WIDTH - 40, HEIGHT - 80), font)
    # Watermark bar
    draw.rectangle((0, HEIGHT - 50, WIDTH, HEIGHT), fill=(0, 0, 0, 128))
    draw.text((20, HEIGHT - 42), "Faceless Memebot", fill=COLORS["text_dim"], font=load_font(24))
    return img


def render_drake(captions: Sequence[str]) -> Image.Image:
    """Drake approve/reject two-panel meme."""
    img, draw = _new_canvas()
    reject = captions[0] if captions else "Nah"
    accept = captions[1] if len(captions) > 1 else "Yes"

    panel_h = (HEIGHT - 120) // 2
    left_w = 380

    for i, (text, bg, emoji_color) in enumerate(
        [(reject, COLORS["reject"], COLORS["reject"]), (accept, COLORS["accept"], COLORS["accent2"])]
    ):
        y0 = 60 + i * (panel_h + 20)
        y1 = y0 + panel_h
        _draw_panel(draw, (40, y0, WIDTH - 40, y1), COLORS["bg_panel"])

        # Stylized figure placeholder
        fig_x = 60
        fig_cy = (y0 + y1) // 2
        draw.ellipse((fig_x, fig_cy - 80, fig_x + 160, fig_cy + 80), fill=(50, 50, 60))
        draw.ellipse((fig_x + 30, fig_cy - 120, fig_x + 130, fig_cy - 20), fill=(200, 170, 140))
        arm_y = fig_cy + 20 if i == 1 else fig_cy - 60
        draw.line([(fig_x + 160, fig_cy), (fig_x + 280, arm_y)], fill=emoji_color, width=12)

        _draw_centered_text(
            draw,
            text,
            (left_w + 20, y0 + 40, WIDTH - 60, y1 - 40),
            load_font(52),
        )

    draw.text((20, HEIGHT - 42), "Faceless Memebot • drake", fill=COLORS["text_dim"], font=load_font(22))
    return img


def render_two_panel(captions: Sequence[str]) -> Image.Image:
    """Side-by-side or stacked comparison panels."""
    img, draw = _new_canvas()
    left_title = captions[0] if captions else "Before"
    right_title = captions[1] if len(captions) > 1 else "After"

    gap = 30
    panel_h = (HEIGHT - 180) // 2
    panels = [
        (left_title, COLORS["accent"], 80),
        (right_title, COLORS["accent2"], 80 + panel_h + gap),
    ]

    for text, color, y0 in panels:
        y1 = y0 + panel_h
        _draw_panel(draw, (40, y0, WIDTH - 40, y1), COLORS["bg_panel"])
        draw.rectangle((40, y0, WIDTH - 40, y0 + 12), fill=color)
        _draw_centered_text(draw, text, (60, y0 + 40, WIDTH - 60, y1 - 30), load_font(48))

    draw.text((20, HEIGHT - 42), "Faceless Memebot • two_panel", fill=COLORS["text_dim"], font=load_font(22))
    return img


def render_expanding_brain(captions: Sequence[str]) -> Image.Image:
    """Four-panel expanding brain meme."""
    img, draw = _new_canvas()
    lines = list(captions)
    while len(lines) < 4:
        lines.append(lines[-1] if lines else "...")

    panel_h = (HEIGHT - 200) // 4
    glow_sizes = [40, 60, 80, 110]

    for i in range(4):
        y0 = 60 + i * (panel_h + 10)
        y1 = y0 + panel_h
        _draw_panel(draw, (40, y0, WIDTH - 40, y1), COLORS["bg_panel"])

        cx = 120
        cy = (y0 + y1) // 2
        r = glow_sizes[i]
        glow = Image.new("RGB", (r * 2 + 20, r * 2 + 20), COLORS["bg_panel"])
        glow_draw = ImageDraw.Draw(glow)
        glow_draw.ellipse((10, 10, r * 2 + 10, r * 2 + 10), fill=COLORS["accent2"])
        glow = glow.filter(ImageFilter.GaussianBlur(radius=4))
        img.paste(glow, (cx - r - 10, cy - r - 10))

        brain_draw = ImageDraw.Draw(img)
        brain_draw.ellipse((cx - r // 2, cy - r // 2, cx + r // 2, cy + r // 2), fill=COLORS["accent2"])

        _draw_centered_text(
            brain_draw,
            lines[i],
            (220, y0 + 20, WIDTH - 50, y1 - 20),
            load_font(38),
        )
        draw = brain_draw

    draw.text((20, HEIGHT - 42), "Faceless Memebot • brain", fill=COLORS["text_dim"], font=load_font(22))
    return img


def render_choice(captions: Sequence[str]) -> Image.Image:
    """Two-button choice meme."""
    img, draw = _new_canvas()
    option_a = captions[0] if captions else "Option A"
    option_b = captions[1] if len(captions) > 1 else "Option B"

    # Header
    _draw_centered_text(draw, "CHOOSE WISELY", (40, 60, WIDTH - 40, 200), load_font(64), fill=COLORS["accent"])

    btn_w = WIDTH - 120
    btn_h = 280
    buttons = [
        (option_a, COLORS["reject"], 320),
        (option_b, COLORS["accept"], 320 + btn_h + 60),
    ]

    for text, color, y0 in buttons:
        y1 = y0 + btn_h
        draw.rounded_rectangle((60, y0, 60 + btn_w, y1), radius=30, fill=color, outline=(255, 255, 255), width=3)
        _draw_centered_text(draw, text, (80, y0 + 30, 60 + btn_w - 20, y1 - 30), load_font(46))

    # Sweating figure placeholder
    sx, sy = WIDTH // 2 - 60, 880
    draw.ellipse((sx, sy, sx + 120, sy + 120), fill=(200, 170, 140))
    for drop_x in (sx + 20, sx + 90):
        draw.polygon([(drop_x, sy + 100), (drop_x + 8, sy + 140), (drop_x + 16, sy + 100)], fill=(100, 180, 255))

    draw.text((20, HEIGHT - 42), "Faceless Memebot • choice", fill=COLORS["text_dim"], font=load_font(22))
    return img


RENDERERS = {
    "classic": render_classic,
    "drake": render_drake,
    "two_panel": render_two_panel,
    "expanding_brain": render_expanding_brain,
    "choice": render_choice,
}


def render_meme(template_name: str, captions: Sequence[str]) -> Image.Image:
    if template_name.startswith("custom_"):
        from memebot.templates.custom import discover_custom_templates, render_custom_background

        custom = discover_custom_templates()
        bg_path = custom.get(template_name)
        if bg_path:
            return render_custom_background(bg_path, list(captions))
        raise ValueError(f"Custom template not found: {template_name}")

    renderer = RENDERERS.get(template_name, render_classic)
    if template_name == "expanding_brain":
        # Brain meme uses up to 4 lines; pad from 2 captions
        if len(captions) == 2:
            captions = [captions[0], captions[1], captions[1], captions[1]]
    return renderer(captions)
