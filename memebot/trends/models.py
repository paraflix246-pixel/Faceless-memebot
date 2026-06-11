"""Trend/topic data models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Topic:
    """A trending topic or headline to meme-ify."""

    title: str
    source: str
    url: str | None = None
    score: int = 0
