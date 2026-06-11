"""Aggregate trend sources with Reddit OAuth, public Reddit, HN, and fallback."""

from __future__ import annotations

import logging

from memebot.config import Settings
from memebot.trends.fallback import FallbackTrendSource
from memebot.trends.hackernews import HackerNewsTrendSource
from memebot.trends.models import Topic
from memebot.trends.reddit import RedditTrendSource
from memebot.trends.reddit_oauth import RedditOAuthTrendSource

logger = logging.getLogger(__name__)


def fetch_topics(settings: Settings, limit: int = 10) -> list[Topic]:
    """Fetch topics from Reddit OAuth, public Reddit, HN, then curated fallback."""
    topics: list[Topic] = []

    if settings.reddit_oauth_configured():
        try:
            oauth = RedditOAuthTrendSource(settings)
            topics = oauth.fetch(limit=limit)
            logger.info("Reddit OAuth returned %d topics", len(topics))
        except Exception as exc:
            logger.warning("Reddit OAuth failed (%s); falling back to public API", exc)

    if len(topics) < limit:
        reddit = RedditTrendSource(settings.reddit_subreddits)
        public = reddit.fetch(limit=limit - len(topics))
        seen = {t.title.lower() for t in topics}
        for topic in public:
            if topic.title.lower() not in seen:
                topics.append(topic)
                seen.add(topic.title.lower())

    if len(topics) < limit:
        logger.info("Reddit returned %d topics; trying Hacker News", len(topics))
        hn = HackerNewsTrendSource().fetch(limit=limit - len(topics))
        seen = {t.title.lower() for t in topics}
        for topic in hn:
            if topic.title.lower() not in seen:
                topics.append(topic)
                seen.add(topic.title.lower())

    if len(topics) < limit:
        logger.info("Live sources returned %d topics; supplementing with fallback", len(topics))
        fallback = FallbackTrendSource().fetch(limit=limit - len(topics))
        seen = {t.title.lower() for t in topics}
        for topic in fallback:
            if topic.title.lower() not in seen:
                topics.append(topic)
                seen.add(topic.title.lower())

    if not topics:
        logger.warning("All trend sources failed; using fallback only")
        topics = FallbackTrendSource().fetch(limit=limit)

    return topics[:limit]
