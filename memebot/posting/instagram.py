"""Instagram Graph API posting integration."""

from __future__ import annotations

import logging
import time

import requests

from memebot.posting.base import PlatformPoster, PostContext, PostResult

logger = logging.getLogger(__name__)

GRAPH_URL = "https://graph.facebook.com/v19.0"


class InstagramPoster(PlatformPoster):
    platform = "instagram"

    def is_configured(self) -> bool:
        return bool(self.settings.instagram_access_token and self.settings.instagram_account_id)

    def post(self, ctx: PostContext) -> PostResult:
        if ctx.dry_run or not self.is_configured():
            detail = "credentials OK" if self.is_configured() else "missing INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCOUNT_ID"
            return self._dry_run_result(ctx, detail)

        token = self.settings.instagram_access_token
        account_id = self.settings.instagram_account_id

        try:
            # Step 1: create media container (requires publicly accessible image URL in production)
            create_url = f"{GRAPH_URL}/{account_id}/media"
            payload = {
                "caption": ctx.caption[:2200],
                "access_token": token,
            }
            # For local files, Graph API needs a hosted URL — log limitation
            logger.warning(
                "Instagram Graph API requires a public image URL; "
                "upload %s to hosting first for production use.",
                ctx.image_path.name,
            )
            resp = requests.post(create_url, data=payload, timeout=30)
            if resp.status_code >= 400:
                return PostResult(
                    platform=self.platform,
                    success=False,
                    message=f"Instagram container failed: {resp.text}",
                )
            container_id = resp.json().get("id")
            if not container_id:
                return PostResult(platform=self.platform, success=False, message="No container id returned")

            time.sleep(2)
            publish_url = f"{GRAPH_URL}/{account_id}/media_publish"
            pub = requests.post(
                publish_url,
                data={"creation_id": container_id, "access_token": token},
                timeout=30,
            )
            if pub.status_code >= 400:
                return PostResult(platform=self.platform, success=False, message=pub.text)
            post_id = pub.json().get("id")
            return PostResult(
                platform=self.platform,
                success=True,
                message=f"Posted to Instagram ({post_id})",
                post_id=str(post_id),
            )
        except Exception as exc:
            logger.error("Instagram post failed: %s", exc)
            return PostResult(platform=self.platform, success=False, message=str(exc))
