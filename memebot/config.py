"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
TEMPLATES_DIR = ASSETS_DIR / "templates"
APPROVED_DIR = PROJECT_ROOT / "output" / "approved"


@dataclass
class Settings:
    """Runtime settings for the meme pipeline."""

    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output")
    approved_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "output" / "approved")
    niche: str = "memes"
    reddit_subreddits: list[str] = field(default_factory=lambda: ["memes"])
    batch_size: int = 5
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    llm_provider: str = "auto"
    log_level: str = "INFO"
    scheduler_timezone: str = "UTC"
    # Reddit OAuth (optional; falls back to public JSON API)
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str | None = None
    # Video export
    video_duration: float = 5.0
    video_fps: int = 30
    # Social posting credentials
    twitter_api_key: str | None = None
    twitter_api_secret: str | None = None
    twitter_access_token: str | None = None
    twitter_access_secret: str | None = None
    instagram_access_token: str | None = None
    instagram_account_id: str | None = None
    tiktok_access_token: str | None = None
    youtube_api_key: str | None = None
    youtube_oauth_token: str | None = None

    @classmethod
    def from_env(cls) -> Settings:
        subreddits_raw = os.getenv("REDDIT_SUBREDDITS", os.getenv("NICHE", "memes"))
        subreddits = [s.strip() for s in subreddits_raw.split(",") if s.strip()]

        output = os.getenv("OUTPUT_DIR", "output")
        output_path = Path(output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path

        approved = os.getenv("APPROVED_DIR", str(output_path / "approved"))
        approved_path = Path(approved)
        if not approved_path.is_absolute():
            approved_path = PROJECT_ROOT / approved_path

        return cls(
            output_dir=output_path,
            approved_dir=approved_path,
            niche=os.getenv("NICHE", "memes"),
            reddit_subreddits=subreddits or ["memes"],
            batch_size=int(os.getenv("BATCH_SIZE", "5")),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
            llm_provider=os.getenv("LLM_PROVIDER", "auto").lower(),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
            scheduler_timezone=os.getenv("SCHEDULER_TIMEZONE", "UTC"),
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID") or None,
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET") or None,
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT") or None,
            video_duration=float(os.getenv("VIDEO_DURATION", "5.0")),
            video_fps=int(os.getenv("VIDEO_FPS", "30")),
            twitter_api_key=os.getenv("TWITTER_API_KEY") or None,
            twitter_api_secret=os.getenv("TWITTER_API_SECRET") or None,
            twitter_access_token=os.getenv("TWITTER_ACCESS_TOKEN") or None,
            twitter_access_secret=os.getenv("TWITTER_ACCESS_SECRET") or None,
            instagram_access_token=os.getenv("INSTAGRAM_ACCESS_TOKEN") or None,
            instagram_account_id=os.getenv("INSTAGRAM_ACCOUNT_ID") or None,
            tiktok_access_token=os.getenv("TIKTOK_ACCESS_TOKEN") or None,
            youtube_api_key=os.getenv("YOUTUBE_API_KEY") or None,
            youtube_oauth_token=os.getenv("YOUTUBE_OAUTH_TOKEN") or None,
        )

    def resolved_llm_provider(self, force: bool = False) -> str | None:
        if self.llm_provider == "none" and not force:
            return None
        if self.llm_provider == "openai" and self.openai_api_key:
            return "openai"
        if self.llm_provider == "anthropic" and self.anthropic_api_key:
            return "anthropic"
        if self.llm_provider == "auto" or force:
            if self.openai_api_key:
                return "openai"
            if self.anthropic_api_key:
                return "anthropic"
        return None

    def reddit_oauth_configured(self) -> bool:
        return bool(
            self.reddit_client_id
            and self.reddit_client_secret
            and self.reddit_user_agent
        )


def get_settings() -> Settings:
    return Settings.from_env()
