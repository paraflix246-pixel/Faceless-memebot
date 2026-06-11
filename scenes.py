"""Stage 2: Scene breakdown from script JSON."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pipeline_log import log_info, record_fallback

if TYPE_CHECKING:
    from content_types.base import BaseContentType, ScriptResult


@dataclass
class Scene:
    id: int
    narration: str
    image_prompt: str
    duration: float = 6.0


def breakdown_scenes(
    script: "ScriptResult",
    content_type: "BaseContentType",
) -> list[Scene]:
    """Parse script scenes or build from manual templates."""
    scenes: list[Scene] = []

    if script.scenes and len(script.scenes) >= 3:
        for i, raw in enumerate(script.scenes):
            narration = str(raw.get("narration", "")).strip()
            prompt = str(raw.get("image_prompt", "")).strip()
            if not narration:
                continue
            if not prompt:
                prompt = f"Scene {i + 1}: {narration[:80]}, {content_type.image_style_suffix()}"
            scenes.append(
                Scene(
                    id=int(raw.get("id", i + 1)),
                    narration=narration,
                    image_prompt=f"{prompt}, {content_type.image_style_suffix()}",
                )
            )
        if scenes:
            _assign_durations(scenes, target_total=45.0)
            log_info("scenes", f"Parsed {len(scenes)} scenes from script JSON")
            return scenes

    record_fallback("manual_scene_templates")
    log_info("scenes", "Using manual scene template fallback")
    parts = _split_narration(script)
    colors_hint = content_type.placeholder_colors()
    for i, narration in enumerate(parts):
        scenes.append(
            Scene(
                id=i + 1,
                narration=narration,
                image_prompt=(
                    f"{content_type.name} scene about {narration[:60]}, "
                    f"{content_type.image_style_suffix()}"
                ),
            )
        )
    _assign_durations(scenes, target_total=45.0)
    return scenes


def _split_narration(script: "ScriptResult") -> list[str]:
    segments = [script.hook]
    sentences = [s.strip() for s in script.body.replace("\n", " ").split(".") if s.strip()]
    chunk_size = max(1, len(sentences) // 4)
    for i in range(0, len(sentences), chunk_size):
        chunk = ". ".join(sentences[i : i + chunk_size])
        if chunk and not chunk.endswith("."):
            chunk += "."
        segments.append(chunk)
    segments.append(script.closing_question)
    return [s for s in segments if s]


def _assign_durations(scenes: list[Scene], target_total: float = 45.0) -> None:
    """Distribute scene durations to hit ~30-60s total."""
    n = len(scenes)
    if n == 0:
        return
    per_scene = max(5.0, min(10.0, target_total / n))
    for scene in scenes:
        word_count = len(scene.narration.split())
        scene.duration = max(5.0, min(10.0, word_count * 0.45))


def scene_narration_text(scenes: list[Scene]) -> str:
    return " ".join(s.narration for s in scenes)
