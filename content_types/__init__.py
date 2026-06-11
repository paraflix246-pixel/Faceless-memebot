"""Content type registry for Shorts Factory Bot."""

from content_types.anime import AnimeContentType
from content_types.base import BaseContentType
from content_types.cyber import CyberContentType
from content_types.versus import VersusContentType
from content_types.what_if import WhatIfContentType

CONTENT_TYPES: dict[str, type[BaseContentType]] = {
    "what_if": WhatIfContentType,
    "versus": VersusContentType,
    "anime": AnimeContentType,
    "cyber": CyberContentType,
}


def get_content_type(name: str) -> BaseContentType:
    key = name.lower().replace("-", "_")
    if key not in CONTENT_TYPES:
        raise ValueError(f"Unknown content type: {name}. Choose from: {', '.join(CONTENT_TYPES)}")
    return CONTENT_TYPES[key]()
