"""Optional PNG → 9:16 MP4 export with Ken Burns zoom effect."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MOVIEPY_AVAILABLE = False
_import_error: str | None = None

try:
    from moviepy import ImageClip
    from moviepy.video.fx import FadeIn

    MOVIEPY_AVAILABLE = True
except ImportError:
    try:
        from moviepy.editor import ImageClip  # type: ignore[no-redef]

        MOVIEPY_AVAILABLE = True
        FadeIn = None  # type: ignore[assignment,misc]
    except ImportError as exc:
        _import_error = str(exc)


def moviepy_status() -> tuple[bool, str | None]:
    """Return (available, error_message)."""
    if MOVIEPY_AVAILABLE:
        return True, None
    return False, _import_error or "moviepy not installed"


def png_to_video(
    png_path: Path,
    output_path: Path | None = None,
    *,
    duration: float = 5.0,
    fps: int = 30,
    zoom_end: float = 1.12,
) -> Path:
    """Convert a portrait PNG to MP4 with Ken Burns zoom + fade-in."""
    available, err = moviepy_status()
    if not available:
        raise ImportError(
            f"moviepy is required for video export. Install with: pip install moviepy. ({err})"
        )

    png_path = Path(png_path)
    if not png_path.exists():
        raise FileNotFoundError(png_path)

    out = output_path or png_path.with_suffix(".mp4")
    out.parent.mkdir(parents=True, exist_ok=True)

    clip = ImageClip(str(png_path), duration=duration)

    # Ken Burns: slow zoom from center
    def zoom(t: float) -> float:
        progress = t / duration if duration else 0
        return 1.0 + (zoom_end - 1.0) * progress

    zoomed = clip.resized(zoom)
    if FadeIn is not None:
        zoomed = zoomed.with_effects([FadeIn(0.5)])

    zoomed.write_videofile(
        str(out),
        fps=fps,
        codec="libx264",
        audio=False,
        logger=None,
    )
    zoomed.close()
    clip.close()

    logger.info("Video exported: %s", out.name)
    return out


def export_videos_for_memes(
    image_paths: list[Path],
    *,
    duration: float = 5.0,
    fps: int = 30,
) -> list[Path]:
    """Export MP4 for each PNG; skip failures with warning."""
    videos: list[Path] = []
    for png in image_paths:
        try:
            videos.append(png_to_video(png, duration=duration, fps=fps))
        except Exception as exc:
            logger.warning("Video export failed for %s: %s", png.name, exc)
    return videos
