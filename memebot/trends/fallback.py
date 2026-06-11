"""Curated fallback topics when live trend APIs are unavailable."""

from __future__ import annotations

import random

from memebot.trends.models import Topic

FALLBACK_TOPICS = [
    "When the code works on the first try",
    "Monday morning standup energy",
    "AI replacing jobs vs AI needing a GPU farm",
    "That one coworker who replies-all",
    "Trying to explain crypto to your parents",
    "When WiFi drops during a video call",
    "Productivity hacks that last exactly one day",
    "The gym membership you haven't used since January",
    "Notifications at 3 AM for no reason",
    "When autocorrect ruins your professional email",
    "Remote work: pajama pants, formal shirt",
    "Reading terms and conditions like a responsible adult",
    "Coffee count: yes",
    "When your phone battery hits 1% in an emergency",
    "Explaining memes to someone born before 1990",
    "The group chat when plans actually happen",
    "Weekend plans vs Sunday scaries",
    "When the delivery arrives right as you leave",
    "Trying to look busy when the boss walks by",
    "That feeling when payday hits and bills say hello",
]


class FallbackTrendSource:
    """Return shuffled curated topics — always available offline."""

    def fetch(self, limit: int = 10) -> list[Topic]:
        picks = random.sample(FALLBACK_TOPICS, k=min(limit, len(FALLBACK_TOPICS)))
        return [
            Topic(title=title, source="curated/fallback", score=100 - i)
            for i, title in enumerate(picks)
        ]
