"""Fetch hot posts from Reddit (no API key required)."""

from __future__ import annotations

import logging
from typing import Sequence

import requests

from memebot.trends.models import Topic

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


class RedditTrendSource:
    """Pull trending titles from Reddit subreddit hot lists."""

    def __init__(self, subreddits: Sequence[str], timeout: float = 10.0) -> None:
        self.subreddits = list(subreddits)
        self.timeout = timeout

    def fetch(self, limit: int = 10) -> list[Topic]:
        topics: list[Topic] = []
        per_sub = max(limit // max(len(self.subreddits), 1), 3)

        for subreddit in self.subreddits:
            try:
                topics.extend(self._fetch_subreddit(subreddit, per_sub))
            except Exception as exc:
                logger.warning("Reddit fetch failed for r/%s: %s", subreddit, exc)

        topics.sort(key=lambda t: t.score, reverse=True)
        seen: set[str] = set()
        unique: list[Topic] = []
        for topic in topics:
            key = topic.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(topic)
        return unique[:limit]

    def _fetch_subreddit(self, subreddit: str, limit: int) -> list[Topic]:
        url = f"https://old.reddit.com/r/{subreddit}/hot.json"
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        }
        response = requests.get(
            url,
            headers=headers,
            params={"limit": min(limit * 2, 50)},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        topics: list[Topic] = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("stickied") or post.get("over_18"):
                continue
            title = (post.get("title") or "").strip()
            if not title or len(title) < 10:
                continue
            topics.append(
                Topic(
                    title=title,
                    source=f"reddit/r/{subreddit}",
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    score=int(post.get("score", 0)),
                )
            )
            if len(topics) >= limit:
                break
        logger.info("Fetched %d topics from r/%s", len(topics), subreddit)
        return topics
