"""Fetch trending stories from Hacker News (no API key required)."""

from __future__ import annotations

import logging

import requests

from memebot.trends.models import Topic

logger = logging.getLogger(__name__)

TOP_STORIES_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{id}.json"


class HackerNewsTrendSource:
    """Pull top story titles from Hacker News."""

    def __init__(self, timeout: float = 10.0) -> None:
        self.timeout = timeout

    def fetch(self, limit: int = 10) -> list[Topic]:
        response = requests.get(TOP_STORIES_URL, timeout=self.timeout)
        response.raise_for_status()
        story_ids = response.json()[: limit * 2]

        topics: list[Topic] = []
        for story_id in story_ids:
            if len(topics) >= limit:
                break
            try:
                item_resp = requests.get(
                    ITEM_URL.format(id=story_id),
                    timeout=self.timeout,
                )
                item_resp.raise_for_status()
                item = item_resp.json()
            except Exception as exc:
                logger.debug("HN item %s failed: %s", story_id, exc)
                continue

            title = (item.get("title") or "").strip()
            if not title or len(title) < 10:
                continue
            topics.append(
                Topic(
                    title=title,
                    source="hackernews/top",
                    url=item.get("url") or f"https://news.ycombinator.com/item?id={story_id}",
                    score=int(item.get("score", 0)),
                )
            )

        logger.info("Fetched %d topics from Hacker News", len(topics))
        return topics
