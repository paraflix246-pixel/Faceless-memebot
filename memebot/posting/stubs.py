"""Social media posting stubs — backward-compatible wrapper."""

from __future__ import annotations

import logging
from pathlib import Path

from memebot.config import get_settings
from memebot.posting.runner import post_to_all

logger = logging.getLogger(__name__)


class PostingError(Exception):
    """Raised when a social post fails."""


def post_to_twitter(image_path: Path, caption: str) -> None:
    settings = get_settings()
    result = post_to_all(["x"], settings, dry_run=False, image_path=image_path)
    r = result.get("x")
    if r and not r.success:
        raise PostingError(r.message)


def post_to_instagram(image_path: Path, caption: str) -> None:
    settings = get_settings()
    result = post_to_all(["instagram"], settings, dry_run=False, image_path=image_path)
    r = result.get("instagram")
    if r and not r.success:
        raise PostingError(r.message)


def post_to_tiktok(video_path: Path, caption: str) -> None:
    settings = get_settings()
    result = post_to_all(["tiktok"], settings, dry_run=False, image_path=video_path)
    r = result.get("tiktok")
    if r and not r.success:
        raise PostingError(r.message)


def post_to_youtube(video_path: Path, title: str, description: str) -> None:
    settings = get_settings()
    result = post_to_all(["youtube"], settings, dry_run=False, image_path=video_path)
    r = result.get("youtube")
    if r and not r.success:
        raise PostingError(r.message)


def publish_meme(image_path: Path, captions: list[str], platforms: list[str] | None = None) -> dict[str, str]:
    """Attempt to publish to requested platforms. Returns status per platform."""
    settings = get_settings()
    caption = " | ".join(captions)
    platform_map = {
        "twitter": "x",
        "x": "x",
        "instagram": "instagram",
        "tiktok": "tiktok",
        "youtube": "youtube",
    }
    mapped = [platform_map.get(p.lower(), p.lower()) for p in (platforms or [])]
    results = post_to_all(mapped, settings, dry_run=False, image_path=image_path)

    status: dict[str, str] = {}
    for platform, result in results.items():
        if result.success:
            status[platform] = "posted" if not result.dry_run else "dry-run ok"
        else:
            status[platform] = f"error: {result.message}"
    return status
