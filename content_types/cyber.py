"""Cybersecurity explainer content type."""

from __future__ import annotations

from content_types.base import BaseContentType


class CyberContentType(BaseContentType):
    name = "cyber"
    scene_count = 6

    def prompt_template(self, topic: str, *, make_longer: bool = False) -> str:
        length_note = (
            "Make the script LONGER — 180-200 words, 7-8 educational scenes."
            if make_longer
            else "Aim for 150-170 words with 6 scenes."
        )
        return f"""You are a viral YouTube Shorts scriptwriter for cybersecurity awareness.

Topic: {topic}

{length_note}

Return ONLY valid JSON:
{{
  "hook": "Alarming or surprising cyber fact in 1 sentence",
  "body": "Explain the threat simply — how it works, real-world impact, how to protect yourself",
  "closing_question": "Ask if viewers have experienced this",
  "scenes": [
    {{"id": 1, "narration": "...", "image_prompt": "cyberpunk/hacker visual metaphor"}},
    ... 6 scenes
  ]
}}

Rules:
- Write ALL narration, hook, body, and closing question in English only
- No step-by-step hacking instructions — awareness only
- Use analogies non-technical viewers understand
- Image prompts: cyberpunk aesthetic, neon, matrix-style, vertical 9:16, no readable text"""

    def voice(self) -> str:
        return "en-US-JennyNeural"

    def image_style_suffix(self) -> str:
        return "cyberpunk, neon glow, digital security theme, vertical 9:16"

    def placeholder_colors(self) -> list[tuple[int, int, int]]:
        return [
            (0, 255, 136),
            (0, 40, 80),
            (20, 20, 40),
            (0, 180, 255),
            (40, 0, 60),
            (0, 100, 60),
        ]
