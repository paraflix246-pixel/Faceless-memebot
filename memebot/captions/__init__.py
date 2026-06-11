"""Caption generation for meme templates."""

from __future__ import annotations

import logging
import random
import re

from memebot.config import Settings
from memebot.trends.models import Topic

logger = logging.getLogger(__name__)

# Template caption patterns keyed by meme format name
CAPTION_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "classic": [
        ("WHEN {topic}", "BUT ALSO {topic}"),
        ("NO ONE:", "ME: {topic}"),
        ("{topic}", "STILL {topic}"),
    ],
    "drake": [
        ("Doing things the hard way", "{topic}"),
        ("Ignoring {topic}", "Embracing {topic}"),
    ],
    "two_panel": [
        ("Expectation: {topic}", "Reality: {topic}"),
        ("What I ordered: {topic}", "What I got: {topic}"),
    ],
    "expanding_brain": [
        ("Not thinking about {topic}", "Thinking about {topic}"),
        ("Researching {topic}", "Becoming {topic}"),
        ("Transcending {topic}", "You ARE {topic}"),
    ],
    "choice": [
        ("Option A: ignore it", "Option B: {topic}"),
        ("Sleep", "{topic} at 2 AM"),
    ],
}

SHORTEN_RE = re.compile(r"\s+")


def _shorten(text: str, max_len: int = 60) -> str:
    text = SHORTEN_RE.sub(" ", text.strip())
    if len(text) <= max_len:
        return text
    return text[: max_len - 3].rsplit(" ", 1)[0] + "..."


def generate_template_captions(topic: Topic, template_name: str) -> list[str]:
    """Build caption lines from topic title using template patterns."""
    short_topic = _shorten(topic.title, 50)
    patterns = CAPTION_PATTERNS.get(template_name, CAPTION_PATTERNS["classic"])
    top, bottom = random.choice(patterns)
    return [
        top.format(topic=short_topic).upper() if template_name == "classic" else top.format(topic=short_topic),
        bottom.format(topic=short_topic).upper() if template_name == "classic" else bottom.format(topic=short_topic),
    ]


def generate_captions(
    topic: Topic,
    template_name: str,
    settings: Settings,
    *,
    force_llm: bool = False,
) -> list[str]:
    """Generate captions via LLM if configured (or forced), else template-based."""
    provider = settings.resolved_llm_provider(force=force_llm)
    if force_llm and not provider:
        raise ValueError(
            "No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
        )
    if provider:
        try:
            from memebot.captions.llm import generate_llm_captions

            return generate_llm_captions(topic, template_name, settings, provider)
        except Exception as exc:
            if force_llm:
                raise
            logger.warning("LLM caption failed (%s); using template fallback", exc)

    return generate_template_captions(topic, template_name)
