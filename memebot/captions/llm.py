"""Optional LLM-powered caption generation."""

from __future__ import annotations

import json
import logging
import re

from memebot.config import Settings
from memebot.trends.models import Topic

logger = logging.getLogger(__name__)

TEMPLATE_HINTS = {
    "classic": "top/bottom impact meme — punchy setup and punchline",
    "drake": "Drake reject/approve — first line is the bad option, second is the good one",
    "two_panel": "before/after or expectation vs reality comparison",
    "expanding_brain": "escalating levels of enlightenment (return 2 lines; we expand to 4)",
    "choice": "painful dilemma — two buttons, relatable struggle",
}


def _build_prompt(topic: Topic, template_name: str) -> str:
    hint = TEMPLATE_HINTS.get(template_name, "funny meme captions")
    custom_note = ""
    if template_name.startswith("custom_"):
        custom_note = " This uses a custom background — keep text short and readable on image overlays."

    return (
        "You are a viral meme caption writer for TikTok/Reels. "
        f"Write captions for a '{template_name}' meme ({hint}).{custom_note}\n\n"
        f"Topic/headline: \"{topic.title}\"\n"
        f"Source: {topic.source}\n\n"
        "Rules:\n"
        "- Return EXACTLY 2 caption strings as a JSON array\n"
        "- Max 70 characters per line\n"
        "- Internet-native humor: ironic, relatable, slightly absurd\n"
        "- No hashtags, no emojis, no explanation\n"
        "- Reference the topic obliquely — don't quote the headline verbatim\n"
        "- Make it actually funny, not corporate\n\n"
        'Example output: ["When the meeting could\'ve been an email", "But it\'s a 2hr Zoom"]'
    )


def generate_llm_captions(
    topic: Topic,
    template_name: str,
    settings: Settings,
    provider: str,
) -> list[str]:
    prompt = _build_prompt(topic, template_name)

    if provider == "openai":
        text = _call_openai(prompt, settings.openai_api_key)
    elif provider == "anthropic":
        text = _call_anthropic(prompt, settings.anthropic_api_key)
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

    captions = _parse_caption_response(text)
    if len(captions) < 2:
        raise ValueError("LLM returned fewer than 2 captions")
    return captions[:2]


def _parse_caption_response(text: str) -> list[str]:
    text = text.strip()
    match = re.search(r"\[.*?\]", text, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group())
            if isinstance(parsed, list):
                return [str(x).strip() for x in parsed if str(x).strip()]
        except json.JSONDecodeError:
            pass
    lines = [ln.strip().strip('"').strip("'") for ln in text.splitlines() if ln.strip()]
    return lines


def _call_openai(prompt: str, api_key: str | None) -> str:
    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise ImportError("Install openai: pip install openai") from exc

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You write short, funny meme captions. Output only a JSON array of 2 strings.",
            },
            {"role": "user", "content": prompt},
        ],
        max_tokens=150,
        temperature=0.95,
    )
    return response.choices[0].message.content or ""


def _call_anthropic(prompt: str, api_key: str | None) -> str:
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    try:
        import anthropic
    except ImportError as exc:
        raise ImportError("Install anthropic: pip install anthropic") from exc

    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model="claude-3-5-haiku-latest",
        max_tokens=150,
        system="You write short, funny meme captions. Output only a JSON array of 2 strings.",
        messages=[{"role": "user", "content": prompt}],
    )
    block = message.content[0]
    return getattr(block, "text", str(block))
