"""Stage 2: Scene breakdown from script JSON."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from images.character_sources import (
    CharacterMatch,
    build_image_query,
    character_for_scene,
    extract_characters,
)
from pipeline_log import log_info, record_fallback

if TYPE_CHECKING:
    from content_types.base import BaseContentType, ScriptResult


@dataclass
class Scene:
    id: int
    narration: str
    image_prompt: str
    duration: float = 6.0
    character: str = ""
    image_query: str = ""
    character_match: CharacterMatch | None = field(default=None, repr=False)


def breakdown_scenes(
    script: "ScriptResult",
    content_type: "BaseContentType",
) -> list[Scene]:
    """Parse script scenes or build from manual templates with character context."""
    versus = content_type.name == "versus"
    topic_text = f"{script.hook} {script.body} {script.closing_question}"
    all_characters = extract_characters(topic_text)

    scenes: list[Scene] = []

    if script.scenes and len(script.scenes) >= 3:
        for i, raw in enumerate(script.scenes):
            narration = str(raw.get("narration", "")).strip()
            prompt = str(raw.get("image_prompt", "")).strip()
            if not narration:
                continue
            char_name = str(raw.get("character", "")).strip()
            image_query = str(raw.get("image_query", "")).strip()

            scene_chars = extract_characters(f"{narration} {prompt} {char_name}")
            if not scene_chars:
                scene_chars = all_characters
            match = character_for_scene(scene_chars, i, versus=versus)
            if match and not char_name:
                char_name = match.name
            if not image_query and match:
                image_query = build_image_query(match, i, narration, versus=versus)
            elif not image_query:
                image_query = build_image_query(None, i, narration, versus=versus)

            if not prompt:
                if match:
                    prompt = (
                        f"{match.name} from {match.franchise}, "
                        f"{narration[:80]}, {content_type.image_style_suffix()}"
                    )
                else:
                    prompt = f"Scene {i + 1}: {narration[:80]}, {content_type.image_style_suffix()}"

            scenes.append(
                Scene(
                    id=int(raw.get("id", i + 1)),
                    narration=narration,
                    image_prompt=f"{prompt}, {content_type.image_style_suffix()}",
                    character=char_name,
                    image_query=image_query,
                    character_match=match,
                )
            )
        if scenes:
            _assign_durations(scenes, target_total=45.0)
            chars = ", ".join(c.character for c in scenes if c.character) or "none detected"
            log_info("scenes", f"Parsed {len(scenes)} scenes | characters: {chars}")
            return scenes

    record_fallback("manual_scene_templates")
    log_info("scenes", "Using manual scene template fallback")
    parts = _split_narration(script)
    for i, narration in enumerate(parts):
        match = character_for_scene(all_characters, i, versus=versus)
        char_name = match.name if match else ""
        image_query = build_image_query(match, i, narration, versus=versus)
        if match:
            prompt = (
                f"{match.name} from {match.franchise}, {narration[:60]}, "
                f"{content_type.image_style_suffix()}"
            )
        else:
            prompt = (
                f"{content_type.name} scene about {narration[:60]}, "
                f"{content_type.image_style_suffix()}"
            )
        scenes.append(
            Scene(
                id=i + 1,
                narration=narration,
                image_prompt=prompt,
                character=char_name,
                image_query=image_query,
                character_match=match,
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
    for scene in scenes:
        word_count = len(scene.narration.split())
        scene.duration = max(5.0, min(10.0, word_count * 0.45))


def scene_narration_text(scenes: list[Scene]) -> str:
    return " ".join(s.narration for s in scenes)
