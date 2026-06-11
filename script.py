"""Stage 1: Hook & Script generation (DeepSeek → Gemini → mock)."""

from __future__ import annotations

import json
import os
import re
import time
from typing import TYPE_CHECKING

import httpx

from pipeline_log import log_error, log_info, record_fallback

if TYPE_CHECKING:
    from content_types.base import BaseContentType, ScriptResult


def _extract_json(text: str) -> dict | None:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                return None
    return None


def _call_deepseek(prompt: str, *, max_retries: int = 3) -> str | None:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        return None
    base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    model = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You output only valid JSON. No markdown."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 2000,
    }
    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
        except Exception as exc:
            wait = 2**attempt
            log_error("script", f"DeepSeek attempt {attempt + 1}/{max_retries} failed", exc)
            if attempt < max_retries - 1:
                time.sleep(wait)
    return None


def _call_gemini(prompt: str) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            f"Output ONLY valid JSON. No markdown.\n\n{prompt}"
        )
        return response.text
    except Exception as exc:
        log_error("script", "Gemini fallback failed", exc)
        return None


def _mock_script(content_type: "BaseContentType", topic: str) -> "ScriptResult":
    from content_types.base import ScriptResult
    from images.character_sources import (
        build_image_query,
        character_for_scene,
        extract_characters,
    )

    record_fallback("mock_script")
    log_info("script", "Using mock script fallback")
    versus = content_type.name == "versus"
    characters = extract_characters(topic)
    char_names = [c.name for c in characters]
    char_label = " and ".join(char_names) if char_names else topic

    hook = f"What if everything you knew about {char_label} was wrong?"
    body = (
        f"Imagine a world where {topic} plays out completely differently. "
        f"The stakes are higher than anyone expected. Every choice ripples through "
        f"the timeline, reshaping alliances, powers, and destinies. "
        f"Fans have debated this scenario for years, but the truth is wilder than fiction. "
        f"As the story unfolds, familiar rules break down and new legends are born. "
        f"This alternate path reveals hidden strengths, unexpected weaknesses, and a climax "
        f"that would break the internet. The ripple effects touch every character we love, "
        f"forcing them to adapt or fall. In this timeline, nothing stays the same for long."
    )
    question = f"Would this version of {char_label} be better? Drop your take below!"
    scenes = []
    narrations = [
        hook,
        f"Picture the opening scene with {char_label} — but something feels off.",
        f"{char_names[0] if char_names else 'The hero'} faces power shifts nobody predicted."
        if not versus
        else f"{char_names[0] if len(char_names) > 0 else 'Fighter A'} shows their signature move.",
        "Allies become rivals. Rivals find common ground."
        if not versus
        else f"{char_names[1] if len(char_names) > 1 else 'Fighter B'} counters with raw power.",
        f"The final confrontation with {char_label} hits different in this timeline.",
        question,
    ]
    for i, narration in enumerate(narrations, start=1):
        match = character_for_scene(characters, i - 1, versus=versus)
        char_name = match.name if match else ""
        image_query = build_image_query(match, i - 1, narration, versus=versus)
        if match:
            image_prompt = (
                f"{match.name} from {match.franchise}, {match.visual}, "
                f"scene {i}, {content_type.image_style_suffix()}"
            )
        else:
            image_prompt = f"{topic}, scene {i}, {content_type.image_style_suffix()}"
        scenes.append(
            {
                "id": i,
                "narration": narration,
                "character": char_name,
                "image_query": image_query,
                "image_prompt": image_prompt,
            }
        )
    full = f"{hook} {body} {question}"
    return ScriptResult(
        hook=hook,
        body=body,
        closing_question=question,
        full_text=full,
        scenes=scenes,
        source="mock",
    )


def generate_script(
    content_type: "BaseContentType",
    topic: str,
    *,
    make_longer: bool = False,
) -> "ScriptResult":
    """Generate script via DeepSeek → Gemini → mock."""
    from content_types.base import ScriptResult

    prompt = content_type.prompt_template(topic, make_longer=make_longer)

    raw = _call_deepseek(prompt)
    if raw:
        data = _extract_json(raw)
        if data:
            result = content_type.validate_script(data)
            if result:
                result.source = "deepseek"
                log_info("script", f"Script generated via DeepSeek ({len(result.full_text.split())} words)")
                return result
        log_error("script", "DeepSeek returned invalid JSON")

    raw = _call_gemini(prompt)
    if raw:
        data = _extract_json(raw)
        if data:
            result = content_type.validate_script(data)
            if result:
                result.source = "gemini"
                log_info("script", f"Script generated via Gemini ({len(result.full_text.split())} words)")
                return result
        log_error("script", "Gemini returned invalid JSON")
        record_fallback("gemini_script")
    elif os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
        record_fallback("gemini_script")

    return _mock_script(content_type, topic)
