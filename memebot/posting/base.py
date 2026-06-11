"""Shared posting types and helpers."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from memebot.config import Settings

logger = logging.getLogger(__name__)


@dataclass
class PostContext:
    """Media + metadata for a single platform post."""

    image_path: Path
    caption: str
    dry_run: bool = True
    video_path: Path | None = None
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PostResult:
    platform: str
    success: bool
    message: str
    dry_run: bool = False
    post_id: str | None = None


class PlatformPoster(ABC):
    """Base class for social platform posters."""

    platform: str

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True when required credentials are present."""

    @abstractmethod
    def post(self, ctx: PostContext) -> PostResult:
        """Post or dry-run post to the platform."""

    def _dry_run_result(self, ctx: PostContext, detail: str) -> PostResult:
        media = ctx.video_path or ctx.image_path
        logger.info(
            "[DRY-RUN %s] Would post %s | caption: %s | %s",
            self.platform,
            media.name,
            ctx.caption[:80],
            detail,
        )
        return PostResult(
            platform=self.platform,
            success=True,
            message=f"Dry-run: would post to {self.platform} — {detail}",
            dry_run=True,
        )


def find_latest_meme(output_dir: Path) -> tuple[Path, Path | None, dict[str, Any]]:
    """Return (png_path, json_path|None, metadata) for the newest meme in output_dir."""
    pngs = sorted(
        output_dir.glob("*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not pngs:
        raise FileNotFoundError(f"No PNG memes found in {output_dir}")

    png = pngs[0]
    meta_path = png.with_suffix(".json")
    metadata: dict[str, Any] = {}
    if meta_path.exists():
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))

    video = png.with_suffix(".mp4")
    return png, video if video.exists() else None, metadata


def build_caption(metadata: dict[str, Any]) -> str:
    captions = metadata.get("captions") or []
    if captions:
        return " | ".join(str(c) for c in captions)
    topic = metadata.get("topic") or {}
    return str(topic.get("title", "Faceless Memebot"))
