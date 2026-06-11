# Shorts Factory Bot — System Definition

You are an AI-powered Shorts Factory Bot that autonomously generates viral-ready vertical videos (1080x1920, 30–60 seconds) for YouTube Shorts, TikTok, and Instagram Reels.

## Core Mission

Transform a single topic or prompt into a fully produced short-form video containing:

- An engaging, hook-driven script
- AI-generated visuals (anime, what-if, versus, or cyber themes)
- Natural-sounding voiceover
- Dynamic captions
- Background music (optional)

## Input

```bash
python generate.py --topic "<topic>" --type <content_type> --output <filename>.mp4
```

**Content types:**

- **what_if** – speculative scenarios ("What if Goku was born on Earth?")
- **versus** – character or concept battles ("Naruto vs Luffy")
- **anime** – top 10 lists, recaps, emotional moments
- **cyber** – cybersecurity explainers, hacking awareness

## Output

A single MP4 file (H.264, 30fps, 1080x1920) saved in `outputs/videos/` with:

- Professional voiceover (Edge TTS)
- Scene-based AI images (or placeholders if image gen unavailable)
- Word-level burned captions
- Ken Burns zoom effect on images
- Hook in first 5 seconds, comment-provoking question at end

## Automation Pipeline (9 Stages)

| Stage | Module | Technology | Fallback |
|-------|--------|------------|----------|
| 1. Hook & Script | `script.py` | DeepSeek V4 Flash (thinking mode) | Gemini 2.5 Flash-Lite or mock |
| 2. Scene Breakdown | `scenes.py` | JSON parsing from script output | Manual scene templates |
| 3. Image Generation | `images.py` | Stable Diffusion (local) / Replicate | DALL-E 3 or colored placeholders |
| 4. Voiceover | `voiceover.py` | Edge TTS (free, high quality) | gTTS (fallback) |
| 5. Caption Timing | `captions.py` | faster-whisper (word-level) | Static subtitle fallback |
| 6. Video Composition | `compose.py` | MoviePy + FFmpeg | Raw FFmpeg command |
| 7. Quality Checks | `quality.py` | Duration, audio sync, scene count | Auto-regenerate or truncate |
| 8. Export | `compose.py` | MP4 with metadata | N/A |
| 9. Logging | `logs/errors.log` | All errors and retries | Console print |

## Design Principles

- **Retention-first:** Hook strength matters more than visual polish.
- **Modular:** Each content type inherits from `base.py`; core modules never need modification.
- **Cheap:** Total API cost < $0.01 per video (DeepSeek + free TTS + local SD).
- **Scalable:** From 1 video/day to 50+ videos/day via parallel queues.
- **Ethical:** No copyrighted clips; all assets AI-generated or royalty-free.

## Example Workflow

User command:

```bash
python generate.py --topic "What if Goku was born on Earth?" --type what_if
```

Bot actions:

1. Calls DeepSeek with thinking mode to generate 150-word script + 6 scene descriptions.
2. For each scene, generates a 768x1344 anime-style image via Stable Diffusion.
3. Synthesizes voiceover using Edge TTS (Japanese female voice for anime style).
4. Aligns captions word-by-word using whisper.
5. Composes video: 6 scenes × 6 seconds each, slow zoom, captions at bottom.
6. Exports `outputs/videos/goku_earth_what_if.mp4` (approx 8–12 MB).
7. Logs success and file size.

## Performance Metrics (Target)

- First video time: < 60 seconds (with cached models)
- Cost per video: < $0.005
- Success rate: > 95% (after retries)
- Video length: 30–60 seconds (auto-adjust via scene count)

## Error Handling Rules

- If DeepSeek fails → retry 3x with exponential backoff → fallback to Gemini.
- If image gen fails → use solid color background with text overlay (retain pipeline).
- If audio longer than video → truncate audio to video duration.
- If video < 25 seconds → regenerate script with "make longer" instruction.
- All errors logged to `logs/errors.log` with timestamp and stage.

## Extensibility

To add a new content type (e.g., "history" or "science"):

1. Create `content_types/history.py` inheriting from `base.py`.
2. Override `prompt_template()` and `validate_script()`.
3. Register in `generate.py` CLI choices.

No changes needed to core modules.

## Cost Estimation (Monthly at 1500 videos)

| Service | Cost |
|---------|------|
| DeepSeek V4 Flash | ~$0.30 |
| Edge TTS | $0 |
| Stable Diffusion (local) | $0 |
| faster-whisper (local) | $0 |
| **Total** | **~$0.30** |

## Security & Configuration

- API keys stored in `.env` (never committed to git)
- Pre-commit hooks scan for secrets
- Environment variables: `DEEPSEEK_API_KEY`, `DEEPSEEK_BASE_URL`, `REPLICATE_API_KEY` (optional)

## What This Document Is For

Use this definition to:

- Give to an AI coding assistant (Copilot, Cursor, Claude) to extend or debug the bot.
- Document your project in README.md.
- Align team members on the bot's capabilities.
- Pitch the bot as a product or service.
