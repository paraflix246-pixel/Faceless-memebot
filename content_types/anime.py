"""Anime recap / emotional moment content type."""

from __future__ import annotations

from content_types.base import BaseContentType


class AnimeContentType(BaseContentType):
    name = "anime"
    scene_count = 6

    def prompt_template(self, topic: str, *, make_longer: bool = False) -> str:
        length_note = (
            "Make the script LONGER — 180-200 words, 7-8 emotional scenes."
            if make_longer
            else "Aim for 150-170 words with 6 scenes."
        )
        return f"""You are a viral YouTube Shorts scriptwriter for anime content.

Topic: {topic}

{length_note}

Return ONLY valid JSON:
{{
  "hook": "Emotional or shocking hook about this anime topic",
  "body": "Tell the story with passion — lore, twists, character depth",
  "closing_question": "Ask fans a debate question",
  "scenes": [
    {{"id": 1, "narration": "...", "image_prompt": "anime character/scene description"}},
    ... 6 scenes
  ]
}}

Rules:
- Speak like a passionate anime fan
- Reference iconic moments without quoting copyrighted dialogue
- Image prompts: vibrant anime art style, cel-shaded, 9:16 vertical, no text"""

    def voice(self) -> str:
        return "ja-JP-NanamiNeural"

    def image_style_suffix(self) -> str:
        return "vibrant anime art, cel-shaded, emotional scene, vertical 9:16"

    def placeholder_colors(self) -> list[tuple[int, int, int]]:
        return [
            (255, 100, 150),
            (100, 150, 255),
            (255, 200, 80),
            (180, 80, 255),
            (80, 220, 180),
            (255, 130, 80),
        ]
