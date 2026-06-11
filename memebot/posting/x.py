"""X (Twitter) posting integration."""

from __future__ import annotations

import logging

import requests

from memebot.posting.base import PlatformPoster, PostContext, PostResult

logger = logging.getLogger(__name__)


class XPoster(PlatformPoster):
    platform = "x"

    def is_configured(self) -> bool:
        s = self.settings
        return bool(
            s.twitter_api_key
            and s.twitter_api_secret
            and s.twitter_access_token
            and s.twitter_access_secret
        )

    def post(self, ctx: PostContext) -> PostResult:
        if ctx.dry_run or not self.is_configured():
            missing = [] if self.is_configured() else ["TWITTER_API_KEY", "TWITTER_API_SECRET", "TWITTER_ACCESS_TOKEN", "TWITTER_ACCESS_SECRET"]
            detail = "credentials OK" if self.is_configured() else f"missing: {', '.join(missing)}"
            return self._dry_run_result(ctx, detail)

        try:
            import tweepy
        except ImportError:
            return PostResult(
                platform=self.platform,
                success=False,
                message="Install tweepy for live X posting: pip install tweepy",
            )

        try:
            auth = tweepy.OAuth1UserHandler(
                self.settings.twitter_api_key,
                self.settings.twitter_api_secret,
                self.settings.twitter_access_token,
                self.settings.twitter_access_secret,
            )
            api = tweepy.API(auth)
            media = api.media_upload(filename=str(ctx.image_path))
            tweet = api.update_status(status=ctx.caption[:280], media_ids=[media.media_id])
            logger.info("Posted to X: tweet id %s", tweet.id)
            return PostResult(
                platform=self.platform,
                success=True,
                message=f"Posted to X (tweet {tweet.id})",
                post_id=str(tweet.id),
            )
        except Exception as exc:
            logger.error("X post failed: %s", exc)
            return PostResult(platform=self.platform, success=False, message=str(exc))
