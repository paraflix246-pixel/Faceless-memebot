"""YouTube Data API integration for Shorts."""

from __future__ import annotations

import logging

import requests

from memebot.posting.base import PlatformPoster, PostContext, PostResult

logger = logging.getLogger(__name__)

YOUTUBE_UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubePoster(PlatformPoster):
    platform = "youtube"

    def is_configured(self) -> bool:
        return bool(self.settings.youtube_oauth_token)

    def post(self, ctx: PostContext) -> PostResult:
        title = ctx.title or ctx.caption[:100] or "Faceless Memebot Short"
        if ctx.dry_run or not self.is_configured():
            detail = "credentials OK" if self.is_configured() else "missing YOUTUBE_OAUTH_TOKEN"
            if not ctx.video_path:
                detail += " (MP4 required for Shorts)"
            return self._dry_run_result(
                PostContext(
                    image_path=ctx.image_path,
                    caption=ctx.caption,
                    dry_run=ctx.dry_run,
                    video_path=ctx.video_path,
                    title=title,
                    metadata=ctx.metadata,
                ),
                detail,
            )

        if not ctx.video_path:
            return PostResult(
                platform=self.platform,
                success=False,
                message="YouTube Shorts requires an MP4 — generate with --video first",
            )

        try:
            headers = {"Authorization": f"Bearer {self.settings.youtube_oauth_token}"}
            metadata = {
                "snippet": {
                    "title": title,
                    "description": ctx.caption[:5000],
                    "categoryId": "23",
                },
                "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
            }
            params = {"part": "snippet,status", "uploadType": "resumable"}
            init_resp = requests.post(
                YOUTUBE_UPLOAD_URL,
                params=params,
                json=metadata,
                headers={**headers, "Content-Type": "application/json"},
                timeout=30,
            )
            if init_resp.status_code >= 400:
                return PostResult(platform=self.platform, success=False, message=init_resp.text)

            upload_url = init_resp.headers.get("Location")
            if not upload_url:
                return PostResult(platform=self.platform, success=False, message="No upload URL returned")

            with open(ctx.video_path, "rb") as video_file:
                upload_resp = requests.put(
                    upload_url,
                    data=video_file,
                    headers={"Content-Type": "video/mp4"},
                    timeout=120,
                )
            if upload_resp.status_code >= 400:
                return PostResult(platform=self.platform, success=False, message=upload_resp.text)

            video_id = upload_resp.json().get("id", "unknown")
            return PostResult(
                platform=self.platform,
                success=True,
                message=f"Uploaded YouTube Short ({video_id})",
                post_id=str(video_id),
            )
        except Exception as exc:
            logger.error("YouTube post failed: %s", exc)
            return PostResult(platform=self.platform, success=False, message=str(exc))
