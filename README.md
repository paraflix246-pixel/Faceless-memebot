# Faceless Memebot

Automated meme content pipeline for **faceless social media channels** — TikTok, Instagram Reels, YouTube Shorts, and X/Twitter.

Fetch trending topics → pick a meme template → generate portrait-ready images (and optional MP4s) → review → post.

## Features

- **Trend sourcing** — Reddit OAuth (PRAW), public Reddit hot posts, Hacker News, curated fallback
- **5 built-in templates** — classic, drake, two-panel, expanding brain, choice (Pillow-rendered)
- **Custom templates** — drop PNG/JPG backgrounds in `assets/templates/` (auto-discovered)
- **Smart captions** — template-based by default; optional OpenAI/Anthropic with `--llm`
- **9:16 portrait output** — 1080×1920 PNGs ready for Reels/TikTok/Shorts
- **Video export** — optional Ken Burns MP4 via moviepy (`--video` or `memebot video`)
- **Metadata sidecars** — JSON per meme with topic, captions, template, platform hints
- **Batch review UI** — Streamlit gallery with approve/reject → `output/approved/`
- **Social posting** — X, Instagram, TikTok, YouTube modules with dry-run + live modes
- **CLI + scheduler** — generate batches, preview trends, cron via APScheduler

## Quick start

### 1. Clone and set up

```bash
cd C:\Users\shawa\Projects\Faceless-memebot
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
copy .env.example .env
```

### 2. Generate memes

```bash
python -m memebot generate --count 5
python -m memebot generate --count 3 --video --llm
```

Output lands in `output/` as timestamped PNG + JSON pairs (and optional MP4).

### 3. Preview trends only

```bash
python -m memebot trends --limit 10
```

### 4. Convert PNGs to video

```bash
python -m memebot video
python -m memebot video output\my_meme.png
```

### 5. Review before posting

```bash
python -m memebot review
# or: streamlit run memebot/review/app.py
```

Approve moves copies to `output/approved/`; reject moves files to `output/rejected/`.

### 6. Dry-run post (no API keys needed)

```bash
python -m memebot post --platform x --dry-run --latest
python -m memebot post --platform tiktok --latest
python -m memebot post --platform instagram --latest
python -m memebot post --platform youtube --latest
```

### 7. Live post (when credentials configured)

```bash
python -m memebot post --platform x --live --latest
```

### 8. Run on a schedule

```bash
python -m memebot schedule --cron "0 9 * * *" --run-now
```

## CLI reference

| Command | Description |
|---------|-------------|
| `python -m memebot generate [-n COUNT] [-o DIR] [--video] [--llm]` | Generate meme batch |
| `python -m memebot video [PNG ...]` | Export PNG(s) to 9:16 MP4 |
| `python -m memebot trends [-n LIMIT]` | List trending topics |
| `python -m memebot templates` | List built-in + custom templates |
| `python -m memebot post --platform PLATFORM [--dry-run] [--live] [--latest]` | Post or dry-run post |
| `python -m memebot review` | Launch Streamlit review UI |
| `python -m memebot schedule [--cron EXPR] [--run-now]` | Start cron scheduler |

## Environment variables

Copy `.env.example` to `.env`. **No variables are required** — sensible defaults work out of the box.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OUTPUT_DIR` | No | `output` | Where PNG/JSON/MP4 files are saved |
| `APPROVED_DIR` | No | `output/approved` | Approved memes after review |
| `NICHE` | No | `memes` | Primary niche label |
| `REDDIT_SUBREDDITS` | No | `memes` | Comma-separated subreddits for trends |
| `REDDIT_CLIENT_ID` | No | — | Reddit OAuth app client ID |
| `REDDIT_CLIENT_SECRET` | No | — | Reddit OAuth app secret |
| `REDDIT_USER_AGENT` | No | — | Reddit API user agent string |
| `BATCH_SIZE` | No | `5` | Default batch size for `generate` and scheduler |
| `OPENAI_API_KEY` | No | — | Enable OpenAI caption generation |
| `ANTHROPIC_API_KEY` | No | — | Enable Anthropic caption generation |
| `LLM_PROVIDER` | No | `auto` | `auto`, `openai`, `anthropic`, or `none` |
| `VIDEO_DURATION` | No | `5.0` | MP4 length in seconds |
| `VIDEO_FPS` | No | `30` | MP4 frame rate |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `SCHEDULER_TIMEZONE` | No | `UTC` | Timezone for cron scheduler |
| `TWITTER_*` | No | — | X/Twitter API credentials (4 vars) |
| `INSTAGRAM_ACCESS_TOKEN` | No | — | Meta Graph API token |
| `INSTAGRAM_ACCOUNT_ID` | No | — | Instagram business account ID |
| `TIKTOK_ACCESS_TOKEN` | No | — | TikTok Content Posting API token |
| `YOUTUBE_OAUTH_TOKEN` | No | — | OAuth bearer for YouTube uploads |

### Optional packages

```bash
pip install openai anthropic    # for --llm / auto LLM captions
pip install tweepy              # for live X posting
pip install moviepy             # included in requirements.txt
pip install streamlit praw      # included in requirements.txt
```

If `moviepy` is not installed, `--video` gracefully skips MP4 export with a warning.

## Custom templates

Drop background images into `assets/templates/`:

```
assets/templates/
├── README.md
└── my_bg.png    →  template name: custom_my_bg
```

List discovered templates:

```bash
python -m memebot templates
```

See `assets/templates/README.md` for details.

## Project structure

```
Faceless-memebot/
├── assets/templates/       # Custom background images
├── memebot/
│   ├── cli.py              # CLI entry
│   ├── config.py           # Settings from .env
│   ├── captions/           # Template + optional LLM captions
│   ├── generator/          # Pillow renderer, pipeline, video export
│   ├── posting/            # X, Instagram, TikTok, YouTube posters
│   ├── review/             # Streamlit batch review UI
│   ├── scheduler/          # APScheduler cron
│   ├── templates/          # Template registry + custom discovery
│   └── trends/             # Reddit OAuth, HN, fallback sources
├── output/                 # Generated memes (gitignored)
├── requirements.txt
├── .env.example
└── README.md
```

## Meme templates

| Template | Style |
|----------|-------|
| `classic` | Top/bottom impact text on gradient |
| `drake` | Approve/reject two-panel |
| `two_panel` | Stacked comparison |
| `expanding_brain` | Four-panel escalation |
| `choice` | Two-button dilemma |
| `custom_*` | Your background from `assets/templates/` |

Each output includes a JSON metadata file:

```json
{
  "generated_at": "2026-06-11T12:00:00+00:00",
  "topic": { "title": "...", "source": "reddit/r/memes", "score": 1234 },
  "template": "drake",
  "captions": ["...", "..."],
  "video": "20260611_120000_01_drake_topic.mp4",
  "ready_for": ["tiktok", "instagram_reels", "youtube_shorts", "twitter"]
}
```

## License

MIT — use freely for your faceless content channels.
