"""End-to-end meme generation pipeline."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from memebot.captions import generate_captions
from memebot.config import Settings
from memebot.generator.renderer import render_meme
from memebot.templates import pick_template
from memebot.trends.aggregator import fetch_topics
from memebot.trends.models import Topic

logger = logging.getLogger(__name__)


@dataclass
class GeneratedMeme:
    image_path: Path
    metadata_path: Path
    topic: Topic
    template: str
    captions: list[str]
    video_path: Path | None = None


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def generate_batch(
    settings: Settings,
    count: int | None = None,
    *,
    force_llm: bool = False,
    export_video: bool = False,
) -> list[GeneratedMeme]:
    """Fetch trends and generate a batch of meme images."""
    batch_count = count if count is not None else settings.batch_size
    settings.output_dir.mkdir(parents=True, exist_ok=True)

    topics = fetch_topics(settings, limit=batch_count)
    if not topics:
        raise RuntimeError("No topics available for meme generation")

    results: list[GeneratedMeme] = []
    ts = _timestamp()

    for i, topic in enumerate(topics[:batch_count], start=1):
        template = pick_template()
        captions = generate_captions(topic, template, settings, force_llm=force_llm)

        try:
            image = render_meme(template, captions)
        except Exception as exc:
            logger.error("Render failed for topic %r: %s", topic.title, exc)
            continue

        slug = _slugify(topic.title)[:40]
        base_name = f"{ts}_{i:02d}_{template}_{slug}"
        image_path = settings.output_dir / f"{base_name}.png"
        meta_path = settings.output_dir / f"{base_name}.json"

        image.save(image_path, format="PNG", optimize=True)

        video_path: Path | None = None
        if export_video:
            video_path = _try_export_video(image_path, settings)

        metadata = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "topic": asdict(topic),
            "template": template,
            "captions": captions,
            "image": image_path.name,
            "video": video_path.name if video_path else None,
            "ready_for": ["tiktok", "instagram_reels", "youtube_shorts", "twitter"],
        }
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        meme = GeneratedMeme(
            image_path=image_path,
            metadata_path=meta_path,
            topic=topic,
            template=template,
            captions=captions,
            video_path=video_path,
        )
        results.append(meme)
        logger.info("Generated %s (%s)", image_path.name, template)

    return results


def _try_export_video(png_path: Path, settings: Settings) -> Path | None:
    try:
        from memebot.generator.video import png_to_video

        return png_to_video(
            png_path,
            duration=settings.video_duration,
            fps=settings.video_fps,
        )
    except ImportError as exc:
        logger.warning("Video export skipped: %s", exc)
        return None
    except Exception as exc:
        logger.warning("Video export failed: %s", exc)
        return None


def export_video_for_path(png_path: Path, settings: Settings) -> Path:
    """Export a single PNG to MP4."""
    from memebot.generator.video import png_to_video

    return png_to_video(
        png_path,
        duration=settings.video_duration,
        fps=settings.video_fps,
    )


def _slugify(text: str) -> str:
    keep = []
    for ch in text.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in (" ", "-", "_"):
            keep.append("_")
    slug = "".join(keep).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "meme"
