"""Character extraction and web image search for topic-accurate scene visuals."""

from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Sequence

import httpx
from PIL import Image

from pipeline_log import log_error, log_info

_last_ddg_search_at: float = 0.0

OUTPUT_SIZE = (768, 1344)
MIN_IMAGE_BYTES = 8_000
MIN_DIMENSION = 200

# Known characters → franchise + AI/visual descriptors
CHARACTER_REGISTRY: dict[str, dict[str, str | tuple[str, ...]]] = {
    "goku": {
        "name": "Goku",
        "franchise": "Dragon Ball Z",
        "aliases": ("goku", "son goku", "kakarot"),
        "visual": "Dragon Ball Z Goku, spiky black hair, orange gi, muscular, anime screenshot, high quality, 4k",
    },
    "vegeta": {
        "name": "Vegeta",
        "franchise": "Dragon Ball Z",
        "aliases": ("vegeta", "prince vegeta"),
        "visual": "Dragon Ball Z Vegeta, spiky hair, blue Saiyan armor, fierce expression, anime screenshot",
    },
    "naruto": {
        "name": "Naruto Uzumaki",
        "franchise": "Naruto",
        "aliases": ("naruto", "naruto uzumaki", "uzumaki naruto"),
        "visual": "Naruto Uzumaki, blonde spiky hair, orange jumpsuit, headband, anime screenshot, high quality",
    },
    "sasuke": {
        "name": "Sasuke Uchiha",
        "franchise": "Naruto",
        "aliases": ("sasuke", "sasuke uchiha"),
        "visual": "Sasuke Uchiha, dark hair, Sharingan eyes, dark outfit, Naruto anime screenshot",
    },
    "luffy": {
        "name": "Monkey D. Luffy",
        "franchise": "One Piece",
        "aliases": ("luffy", "monkey d luffy", "monkey d. luffy"),
        "visual": "One Piece Luffy, straw hat, red vest, scar under eye, anime screenshot, high quality",
    },
    "zoro": {
        "name": "Roronoa Zoro",
        "franchise": "One Piece",
        "aliases": ("zoro", "roronoa zoro"),
        "visual": "One Piece Zoro, green hair, three swords, muscular, anime action screenshot",
    },
    "ichigo": {
        "name": "Ichigo Kurosaki",
        "franchise": "Bleach",
        "aliases": ("ichigo", "ichigo kurosaki"),
        "visual": "Bleach Ichigo, orange hair, black shinigami robe, large sword, anime screenshot",
    },
    "saitama": {
        "name": "Saitama",
        "franchise": "One Punch Man",
        "aliases": ("saitama", "one punch man"),
        "visual": "One Punch Man Saitama, bald head, yellow suit, red gloves, anime screenshot",
    },
    "eren": {
        "name": "Eren Yeager",
        "franchise": "Attack on Titan",
        "aliases": ("eren", "eren yeager"),
        "visual": "Attack on Titan Eren Yeager, brown hair, Survey Corps uniform, anime screenshot",
    },
    "levi": {
        "name": "Levi Ackerman",
        "franchise": "Attack on Titan",
        "aliases": ("levi", "levi ackerman", "captain levi"),
        "visual": "Attack on Titan Levi Ackerman, short black hair, green cloak, anime screenshot",
    },
    "gojo": {
        "name": "Satoru Gojo",
        "franchise": "Jujutsu Kaisen",
        "aliases": ("gojo", "satoru gojo"),
        "visual": "Jujutsu Kaisen Gojo, white hair, blindfold, black uniform, anime screenshot",
    },
    "tanjiro": {
        "name": "Tanjiro Kamado",
        "franchise": "Demon Slayer",
        "aliases": ("tanjiro", "tanjiro kamado"),
        "visual": "Demon Slayer Tanjiro, burgundy hair, checkered haori, katana, anime screenshot",
    },
    "deku": {
        "name": "Izuku Midoriya",
        "franchise": "My Hero Academia",
        "aliases": ("deku", "izuku", "midoriya"),
        "visual": "My Hero Academia Deku, green hair, green hero costume, anime screenshot",
    },
    "goku_black": {
        "name": "Goku Black",
        "franchise": "Dragon Ball Super",
        "aliases": ("goku black", "black goku"),
        "visual": "Dragon Ball Super Goku Black, pink aura, black gi, anime screenshot",
    },
    "frieza": {
        "name": "Frieza",
        "franchise": "Dragon Ball Z",
        "aliases": ("frieza", "freeza"),
        "visual": "Dragon Ball Z Frieza, white and purple alien form, anime screenshot",
    },
    "sukuna": {
        "name": "Ryomen Sukuna",
        "franchise": "Jujutsu Kaisen",
        "aliases": ("sukuna", "ryomen sukuna"),
        "visual": "Jujutsu Kaisen Sukuna, pink hair, tattoos, evil grin, anime screenshot",
    },
}

SEARCH_QUERY_TEMPLATES: tuple[str, ...] = (
    "{character} {franchise} anime official screenshot HD",
    "{character} {franchise} anime battle scene wallpaper",
    "{character} {franchise} official art portrait vertical",
    "{character} {franchise} anime fight scene 4k",
    "{character} {franchise} manga color panel",
    "{character} {franchise} anime key visual",
)


@dataclass
class CharacterMatch:
    key: str
    name: str
    franchise: str
    visual: str


def extract_characters(text: str) -> list[CharacterMatch]:
    """Find known anime/game characters mentioned in topic or script text."""
    lowered = text.lower()
    found: list[CharacterMatch] = []
    seen_keys: set[str] = set()

    for key, info in CHARACTER_REGISTRY.items():
        aliases = info.get("aliases", (key,))
        if not isinstance(aliases, tuple):
            aliases = (str(aliases),)
        for alias in aliases:
            pattern = r"\b" + re.escape(alias.lower()) + r"\b"
            if re.search(pattern, lowered):
                if key not in seen_keys:
                    seen_keys.add(key)
                    found.append(
                        CharacterMatch(
                            key=key,
                            name=str(info["name"]),
                            franchise=str(info["franchise"]),
                            visual=str(info.get("visual", f"{info['name']} {info['franchise']} anime")),
                        )
                    )
                break

    return found


def character_for_scene(
    characters: Sequence[CharacterMatch],
    scene_index: int,
    *,
    versus: bool = False,
) -> CharacterMatch | None:
    """Pick which character to feature in a scene (alternate for versus)."""
    if not characters:
        return None
    if versus and len(characters) >= 2:
        return characters[scene_index % len(characters)]
    return characters[scene_index % len(characters)]


def build_image_query(
    character: CharacterMatch | None,
    scene_index: int,
    narration: str = "",
    *,
    versus: bool = False,
) -> str:
    """Build a DuckDuckGo image search query with per-scene variety."""
    if character:
        template = SEARCH_QUERY_TEMPLATES[scene_index % len(SEARCH_QUERY_TEMPLATES)]
        return template.format(character=character.name, franchise=character.franchise)
    # Fallback: extract keywords from narration
    snippet = narration[:80].strip() if narration else "anime character"
    return f"{snippet} anime official screenshot HD"


def build_ai_prompt(
    base_prompt: str,
    character: CharacterMatch | None,
    scene_index: int,
) -> str:
    """Enrich AI image prompts with explicit character visual descriptors."""
    if character:
        return (
            f"{character.visual}, {base_prompt}, "
            f"accurate likeness of {character.name} from {character.franchise}, "
            f"anime screenshot style, no text, vertical 9:16"
        )
    return base_prompt


def fit_cover(img: Image.Image, size: tuple[int, int] = OUTPUT_SIZE) -> Image.Image:
    """Scale and center-crop to fill frame (no letterboxing)."""
    tw, th = size
    iw, ih = img.size
    if iw < MIN_DIMENSION or ih < MIN_DIMENSION:
        raise ValueError(f"Image too small: {iw}x{ih}")
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _download_url(url: str, timeout: float) -> bytes | None:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; ShortsFactoryBot/1.0)"})
            resp.raise_for_status()
            content = resp.content
            if len(content) < MIN_IMAGE_BYTES:
                return None
            return content
    except Exception as exc:
        log_error("images", f"Image download failed: {url[:80]}", exc)
        return None


def _validate_and_save(data: bytes, out: Path) -> bool:
    try:
        img = Image.open(BytesIO(data)).convert("RGB")
        fitted = fit_cover(img)
        fitted.save(out)
        return True
    except Exception as exc:
        log_error("images", "Invalid image data from search", exc)
        return False


def _ddg_throttle() -> None:
    """Space out DDG requests to reduce 403 rate-limit errors."""
    global _last_ddg_search_at
    delay = float(os.getenv("DDG_SEARCH_DELAY", "3.0"))
    elapsed = time.monotonic() - _last_ddg_search_at
    if elapsed < delay:
        time.sleep(delay - elapsed)
    _last_ddg_search_at = time.monotonic()


def _ddg_image_results(query: str, max_results: int) -> list[dict]:
    """Run a DuckDuckGo image search with retries on rate limits."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        log_error("images", "duckduckgo-search not installed — pip install duckduckgo-search", None)
        return []

    retries = int(os.getenv("DDG_SEARCH_RETRIES", "3"))
    for attempt in range(retries):
        _ddg_throttle()
        try:
            with DDGS() as ddgs:
                return list(
                    ddgs.images(
                        query,
                        max_results=max_results,
                        size="Large",
                        type_image="photo",
                    )
                )
        except Exception as exc:
            exc_name = type(exc).__name__
            is_rate_limit = "rate" in exc_name.lower() or "403" in str(exc)
            if is_rate_limit and attempt < retries - 1:
                wait = float(os.getenv("DDG_RATE_LIMIT_WAIT", "8")) * (attempt + 1)
                log_info("images", f"DDG rate limit — retry in {wait:.0f}s ({attempt + 1}/{retries})")
                time.sleep(wait)
                continue
            log_error("images", f"DuckDuckGo search failed for: {query[:60]}", exc)
            return []
    return []


def search_character_image(query: str, out: Path, *, result_offset: int = 0) -> str | None:
    """
    Search DuckDuckGo for character images and save the best valid result.
    Returns 'ddg_search' on success.
    """
    if os.getenv("DDG_IMAGE_SEARCH_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return None

    timeout = float(os.getenv("DDG_SEARCH_TIMEOUT", "30"))
    max_results = int(os.getenv("DDG_MAX_RESULTS", "8"))

    results = _ddg_image_results(query, max_results)
    if not results:
        log_info("images", f"No DDG results for: {query[:60]}")
        return None

    # Try results starting at offset for scene variety
    ordered = results[result_offset % len(results) :] + results[: result_offset % len(results)]
    for i, hit in enumerate(ordered[:max_results]):
        url = hit.get("image") or hit.get("thumbnail")
        if not url:
            continue
        data = _download_url(url, timeout)
        if data and _validate_and_save(data, out):
            log_info("images", f"DDG image saved (result #{i + 1}): {query[:50]}")
            return "ddg_search"

    return None
