#!/usr/bin/env python3
"""Shorts Factory Bot — CLI entry point."""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from compose import compose_video
from content_types import get_content_type
from images import generate_scene_images
from pipeline_log import clear_fallbacks, get_fallbacks, log_info, setup_logging
from quality import (
    adjust_scene_durations,
    get_audio_duration,
    get_video_duration,
    needs_longer_script,
    quality_report,
)
from scenes import breakdown_scenes, scene_narration_text
from script import generate_script
from captions import generate_captions
from voiceover import generate_voiceover

OUTPUT_DIR = Path("outputs/videos")
WORK_ROOT = Path("outputs/.work")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Shorts Factory Bot — generate viral-ready vertical shorts"
    )
    parser.add_argument("--topic", required=True, help="Video topic or prompt")
    parser.add_argument(
        "--type",
        required=True,
        choices=["what_if", "versus", "anime", "cyber"],
        help="Content type",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output filename (default: auto from topic)",
    )
    return parser.parse_args()


def _default_output_name(topic: str, content_type: str) -> str:
    slug = "".join(c if c.isalnum() else "_" for c in topic.lower())[:40].strip("_")
    return f"{slug}_{content_type}.mp4"


def run_pipeline(topic: str, content_type_name: str, output: Path) -> Path:
    setup_logging()
    clear_fallbacks()
    content_type = get_content_type(content_type_name)

    work_dir = WORK_ROOT / output.stem
    if work_dir.exists():
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)

    log_info("pipeline", f"Topic: {topic} | Type: {content_type_name}")

    # Stage 1 — script (retry with longer prompt if needed)
    script = generate_script(content_type, topic)
    if needs_longer_script(0, len(script.full_text.split()) * 0.4):
        script = generate_script(content_type, topic, make_longer=True)

    # Stage 2 — scenes
    scenes = breakdown_scenes(script, content_type)
    adjust_scene_durations(scenes, target=45.0)

    # Stage 3 — images
    image_paths = generate_scene_images(scenes, content_type, work_dir / "images")

    # Stage 4 — voiceover
    narration = scene_narration_text(scenes)
    if not narration.strip():
        narration = script.full_text
    audio_path, voice_provider = generate_voiceover(
        narration,
        content_type.voice(),
        work_dir / "voiceover.mp3",
    )

    audio_duration = get_audio_duration(audio_path)
    if audio_duration < 25.0:
        script = generate_script(content_type, topic, make_longer=True)
        scenes = breakdown_scenes(script, content_type)
        adjust_scene_durations(scenes, target=50.0)
        narration = scene_narration_text(scenes)
        audio_path, voice_provider = generate_voiceover(
            narration,
            content_type.voice(),
            work_dir / "voiceover_long.mp3",
        )
        audio_duration = get_audio_duration(audio_path)

    # Stage 5 — captions
    captions, caption_provider = generate_captions(
        audio_path,
        narration,
        audio_duration,
    )

    # Stage 6+8 — compose
    video_duration = max(sum(s.duration for s in scenes), audio_duration, 30.0)
    truncate = audio_duration > video_duration
    output.parent.mkdir(parents=True, exist_ok=True)
    compose_video(
        scenes,
        image_paths,
        audio_path,
        captions,
        output,
        truncate_audio=truncate,
        video_duration=video_duration,
    )

    # Stage 7 — quality
    report = quality_report(output, scenes, audio_duration)
    if needs_longer_script(report["video_duration"], audio_duration):
        log_info("pipeline", "Video too short after compose — acceptable with fallbacks")

    fallbacks = get_fallbacks()
    log_info(
        "pipeline",
        f"Done: {output} | script={script.source} voice={voice_provider} "
        f"captions={caption_provider} fallbacks={fallbacks}",
    )
    return output


def main() -> int:
    load_dotenv()
    args = parse_args()
    out_name = args.output or _default_output_name(args.topic, args.type)
    output = Path(out_name)
    if not output.is_absolute() and output.parent == Path("."):
        output = OUTPUT_DIR / out_name

    try:
        result = run_pipeline(args.topic, args.type, output)
        size_mb = result.stat().st_size / (1024 * 1024)
        duration = get_video_duration(result)
        print(f"\nVideo ready: {result}")
        print(f"  Size: {size_mb:.2f} MB")
        print(f"  Duration: {duration:.1f}s")
        fallbacks = get_fallbacks()
        if fallbacks:
            print(f"  Fallbacks used: {', '.join(fallbacks)}")
        return 0
    except Exception as exc:
        from pipeline_log import log_error

        log_error("pipeline", "Pipeline failed", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
