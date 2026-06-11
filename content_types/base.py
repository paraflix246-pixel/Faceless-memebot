"""Base content type for Shorts Factory Bot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class ScriptResult:
    hook: str
    body: str
    closing_question: str
    full_text: str
    scenes: list[dict] = field(default_factory=list)
    source: str = "mock"


class BaseContentType(ABC):
    """Each content type defines prompts, validation, and voice preferences."""

    name: str = "base"
    min_words: int = 120
    max_words: int = 180
    scene_count: int = 6

    @abstractmethod
    def prompt_template(self, topic: str, *, make_longer: bool = False) -> str:
        """Return the LLM system/user prompt for script generation."""

    def validate_script(self, data: dict) -> ScriptResult | None:
        """Validate parsed JSON script; return None if invalid."""
        hook = str(data.get("hook", "")).strip()
        body = str(data.get("body", "")).strip()
        question = str(data.get("closing_question", "")).strip()
        scenes = data.get("scenes", [])
        if not hook or not body or not question:
            return None
        if not isinstance(scenes, list) or len(scenes) < 3:
            return None
        full = f"{hook} {body} {question}"
        word_count = len(full.split())
        if word_count < self.min_words - 30:
            return None
        return ScriptResult(
            hook=hook,
            body=body,
            closing_question=question,
            full_text=full,
            scenes=scenes,
        )

    def voice(self) -> str:
        """Edge TTS voice ID."""
        return "en-US-GuyNeural"

    def image_style_suffix(self) -> str:
        """Appended to every scene image prompt."""
        return "cinematic, high detail, vertical composition, 9:16 aspect ratio"

    def placeholder_colors(self) -> list[tuple[int, int, int]]:
        """RGB colors for placeholder scene backgrounds."""
        return [
            (30, 30, 60),
            (45, 20, 55),
            (20, 45, 55),
            (55, 30, 20),
            (25, 50, 35),
            (50, 25, 40),
        ]
