"""Trend source protocol."""

from __future__ import annotations

from typing import Protocol

from memebot.trends.models import Topic


class TrendSource(Protocol):
    def fetch(self, limit: int = 10) -> list[Topic]: ...
