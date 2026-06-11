"""Fetch Reddit hot posts via OAuth (PRAW) when credentials are configured."""

from __future__ import annotations

import logging
from typing import Sequence

from memebot.config import Settings
from memebot.trends.models import Topic

logger = logging.getLogger(__name__)


class RedditOAuthTrendSource:
    """Pull trending titles using Reddit OAuth via PRAW."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.subreddits = settings.reddit_subreddits

    def fetch(self, limit: int = 10) -> list[Topic]:
        try:
            import praw
        except ImportError as exc:
            raise ImportError("Install praw for Reddit OAuth: pip install praw") from exc

        reddit = praw.Reddit(
            client_id=self.settings.reddit_client_id,
            client_secret=self.settings.reddit_client_secret,
            user_agent=self.settings.reddit_user_agent,
        )

        topics: list[Topic] = []
        per_sub = max(limit // max(len(self.subreddits), 1), 3)

        for subreddit_name in self.subreddits:
            try:
                subreddit = reddit.subreddit(subreddit_name)
                for submission in subreddit.hot(limit=per_sub * 2):
                    if submission.stickied or submission.over_18:
                        continue
                    title = (submission.title or "").strip()
                    if not title or len(title) < 10:
                        continue
                    topics.append(
                        Topic(
                            title=title,
                            source=f"reddit-oauth/r/{subreddit_name}",
                            url=f"https://reddit.com{submission.permalink}",
                            score=int(submission.score or 0),
                        )
                    )
                    if len([t for t in topics if subreddit_name in t.source]) >= per_sub:
                        break
                logger.info("OAuth fetched topics from r/%s", subreddit_name)
            except Exception as exc:
                logger.warning("Reddit OAuth fetch failed for r/%s: %s", subreddit_name, exc)

        topics.sort(key=lambda t: t.score, reverse=True)
        seen: set[str] = set()
        unique: list[Topic] = []
        for topic in topics:
            key = topic.title.lower().strip()
            if key not in seen:
                seen.add(key)
                unique.append(topic)
        return unique[:limit]
