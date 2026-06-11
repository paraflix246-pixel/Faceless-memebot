"""Versus battle content type."""

from __future__ import annotations

from content_types.base import BaseContentType


class VersusContentType(BaseContentType):
    name = "versus"
    scene_count = 6

    def prompt_template(self, topic: str, *, make_longer: bool = False) -> str:
        length_note = (
            "Make the script LONGER — 180-200 words, 7-8 scenes comparing both sides."
            if make_longer
            else "Aim for 150-170 words with 6 scenes alternating between combatants."
        )
        return f"""You are a viral YouTube Shorts scriptwriter for epic "versus" battles.

Matchup: {topic}

{length_note}

Return ONLY valid JSON:
{{
  "hook": "Dramatic battle announcement in 1 sentence",
  "body": "Compare strengths, weaknesses, signature moves, and who might win",
  "closing_question": "Who wins? Ask viewers to comment",
  "scenes": [
    {{"id": 1, "narration": "...", "image_prompt": "epic battle scene description"}},
    ... 6 scenes
  ]
}}

Rules:
- Write ALL narration, hook, body, and closing question in English only
- Alternate focus between both sides
- Build tension toward a cliffhanger verdict
- Image prompts: dynamic action poses, split-screen feel, anime style, 9:16 vertical"""

    def voice(self) -> str:
        return "en-US-DavisNeural"

    def image_style_suffix(self) -> str:
        return "epic battle scene, anime action, versus matchup, vertical 9:16"
