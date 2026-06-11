"""TikTok Content Posting API integration."""

from __future__ import annotations

import logging

import requests

from memebot.posting.base import PlatformPoster, PostContext, PostResult

logger = logging.getLogger(__name__)

TIKTOK_API = "https://open.tiktokapis.com/v2/post/publish/video/init/"


class TikTokPoster(PlatformPoster):
    platform = "tiktok"

    def is_configured(self) -> bool:
        return bool(self.settings.tiktok_access_token)

    def post(self, ctx: PostContext) -> PostResult:
        media = ctx.video_path or ctx.image_path
        if ctx.dry_run or not self.is_configured():
            detail = "credentials OK" if self.is_configured() else "missing TIKTOK_ACCESS_TOKEN"
            if not ctx.video_path and self.is_configured():
                detail += " (video recommended for TikTok)"
            return self._dry_run_result(
                PostContext(
                    image_path=ctx.image_path,
                    caption=ctx.caption,
                    dry_run=ctx.dry_run,
                    video_path=media if media.suffix == ".mp4" else ctx.video_path,
                    metadata=ctx.metadata,
                ),
                detail,
            )

        if not ctx.video_path:
            return PostResult(
                platform=self.platform,
                success=False,
                message="TikTok requires an MP4 video — run with --video or memebot video",
            )

        try:
            headers = {
                "Authorization": f"Bearer {self.settings.tiktok_access_token}",
                "Content-Type": "application/json",
            }
            body = {
                "post_info": {
                    "title": ctx.caption[:150],
                    "privacy_level": "PUBLIC_TO_EVERYONE",
                },
                "source_info": {"source": "FILE_UPLOAD", "video_size": ctx.video_path.stat().st_size},
            }
            resp = requests.post(TIKTOK_API, json=body, headers=headers, timeout=30)
            if resp.status_code >= 400:
                return PostResult(platform=self.platform, success=False, message=resp.text)
            data = resp.json()
            publish_id = data.get("data", {}).get("publish_id", "unknown")
            return PostResult(
                platform=self.platform,
                success=True,
                message=f"TikTok upload initiated ({publish_id})",
                post_id=str(publish_id),
            )
        except Exception as exc:
            logger.error("TikTok post failed: %s", exc)
            return PostResult(platform=self.platform, success=False, message=str(exc))
