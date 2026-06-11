"""What-if speculative scenario content type."""

from __future__ import annotations

import json

from content_types.base import BaseContentType, ScriptResult


class WhatIfContentType(BaseContentType):
    name = "what_if"
    scene_count = 6

    def prompt_template(self, topic: str, *, make_longer: bool = False) -> str:
        length_note = (
            "Make the script LONGER — aim for 180-200 words total, with 7-8 scenes."
            if make_longer
            else "Aim for 150-170 words total with exactly 6 scenes."
        )
        return f"""You are a viral YouTube Shorts scriptwriter for "what if" scenarios.

Topic: {topic}

Write a retention-optimized script. {length_note}

Return ONLY valid JSON with this structure:
{{
  "hook": "A shocking 1-sentence hook for the first 5 seconds",
  "body": "The main narrative (2-3 paragraphs, conversational, dramatic)",
  "closing_question": "A comment-provoking question for viewers",
  "scenes": [
    {{"id": 1, "narration": "...", "image_prompt": "detailed anime/cinematic visual description"}},
    ... 6 scenes total, each 5-8 seconds of narration
  ]
}}

Rules:
- Write ALL narration, hook, body, and closing question in English only
- Hook must grab attention instantly
- Each scene narration should be 1-2 sentences
- Image prompts: anime style, no text in image, vertical 9:16 framing
- End with an engaging question"""

    def validate_script(self, data: dict) -> ScriptResult | None:
        result = super().validate_script(data)
        if result and not result.hook.lower().startswith("what if"):
            # Allow but don't require — just informational
            pass
        return result

    def voice(self) -> str:
        return "en-US-ChristopherNeural"

    def image_style_suffix(self) -> str:
        return "anime style, dramatic lighting, what-if scenario, vertical 9:16"
