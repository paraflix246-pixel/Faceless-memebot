"""Stage 4: Voiceover synthesis (Edge TTS → gTTS fallback)."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from pipeline_log import log_error, log_info, record_fallback

DEFAULT_ENGLISH_VOICE = os.getenv("EDGE_TTS_VOICE", "en-US-AriaNeural")


def _gtts(text: str, out: Path) -> bool:
    try:
        from gtts import gTTS

        tts = gTTS(text=text, lang="en")
        tts.save(str(out))
        return out.exists() and out.stat().st_size > 0
    except Exception as exc:
        log_error("voiceover", "gTTS fallback failed", exc)
        return False


def generate_voiceover(
    text: str,
    voice: str | None = None,
    out: Path | None = None,
) -> tuple[Path, str]:
    """Synthesize speech; returns (path, provider_used)."""
    if out is None:
        raise ValueError("out path is required")
    if not voice or voice.startswith("ja-"):
        voice = DEFAULT_ENGLISH_VOICE
    out.parent.mkdir(parents=True, exist_ok=True)
    rate = os.getenv("EDGE_TTS_RATE", "+0%")

    async def _run() -> bool:
        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, voice, rate=rate)
            await communicate.save(str(out))
            return out.exists() and out.stat().st_size > 0
        except Exception as exc:
            log_error("voiceover", "Edge TTS failed", exc)
            return False

    if asyncio.run(_run()):
        log_info("voiceover", f"Edge TTS saved to {out.name}")
        return out, "edge_tts"

    record_fallback("gtts_voiceover")
    mp3 = out.with_suffix(".mp3") if out.suffix != ".mp3" else out
    if _gtts(text, mp3):
        log_info("voiceover", f"gTTS fallback saved to {mp3.name}")
        return mp3, "gtts"

    record_fallback("silent_audio")
    _write_silent_wav(out, duration=max(30.0, len(text.split()) * 0.4))
    log_info("voiceover", "Using silent audio fallback")
    return out, "silent"


def _write_silent_wav(path: Path, duration: float) -> None:
    """Minimal WAV file for pipeline continuity when TTS unavailable."""
    import struct
    import wave

    path = path.with_suffix(".wav")
    sample_rate = 44100
    n_frames = int(sample_rate * duration)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsamplewidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<h", 0) * n_frames)
