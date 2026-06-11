"""Trend fetching."""

from memebot.trends.aggregator import fetch_topics
from memebot.trends.models import Topic

__all__ = ["Topic", "fetch_topics"]
