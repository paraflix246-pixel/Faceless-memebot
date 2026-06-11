"""Posting orchestration and CLI helpers."""

from __future__ import annotations

import logging
from pathlib import Path

from memebot.config import Settings
from memebot.posting.base import PostContext, PostResult, build_caption, find_latest_meme
from memebot.posting.instagram import InstagramPoster
from memebot.posting.tiktok import TikTokPoster
from memebot.posting.x import XPoster
from memebot.posting.youtube import YouTubePoster

logger = logging.getLogger(__name__)

PLATFORM_ALIASES = {
    "x": "x",
    "twitter": "x",
    "instagram": "instagram",
    "ig": "instagram",
    "tiktok": "tiktok",
    "youtube": "youtube",
    "yt": "youtube",
}


def get_poster(platform: str, settings: Settings):
    posters = {
        "x": XPoster,
        "instagram": InstagramPoster,
        "tiktok": TikTokPoster,
        "youtube": YouTubePoster,
    }
    key = PLATFORM_ALIASES.get(platform.lower(), platform.lower())
    cls = posters.get(key)
    if not cls:
        raise ValueError(f"Unknown platform: {platform}. Choose: x, instagram, tiktok, youtube")
    return cls(settings)


def post_to_platform(
    platform: str,
    settings: Settings,
    *,
    image_path: Path | None = None,
    video_path: Path | None = None,
    caption: str | None = None,
    dry_run: bool = True,
    use_latest: bool = False,
) -> PostResult:
    """Post (or dry-run) to a single platform."""
    metadata: dict = {}
    if use_latest or image_path is None:
        png, video, metadata = find_latest_meme(settings.output_dir)
        image_path = png
        video_path = video_path or video

    if image_path is None:
        raise ValueError("image_path is required")

    cap = caption or build_caption(metadata)
    poster = get_poster(platform, settings)
    ctx = PostContext(
        image_path=Path(image_path),
        video_path=Path(video_path) if video_path else None,
        caption=cap,
        dry_run=dry_run,
        title=cap[:100],
        metadata=metadata,
    )
    return poster.post(ctx)


def post_to_all(
    platforms: list[str],
    settings: Settings,
    *,
    dry_run: bool = True,
    use_latest: bool = False,
    image_path: Path | None = None,
) -> dict[str, PostResult]:
    results: dict[str, PostResult] = {}
    for platform in platforms:
        try:
            results[platform] = post_to_platform(
                platform,
                settings,
                image_path=image_path,
                dry_run=dry_run,
                use_latest=use_latest,
            )
        except Exception as exc:
            results[platform] = PostResult(platform=platform, success=False, message=str(exc))
    return results
