"""Stage 5: Caption timing (faster-whisper word-level → static fallback)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pipeline_log import log_error, log_info, record_fallback


@dataclass
class CaptionWord:
    word: str
    start: float
    end: float


def generate_captions(
    audio_path: Path,
    fallback_text: str,
    audio_duration: float,
) -> tuple[list[CaptionWord], str]:
    """Return word-level captions and provider name."""
    words = _try_whisper(audio_path)
    if words:
        log_info("captions", f"faster-whisper: {len(words)} words aligned")
        return words, "faster_whisper"

    record_fallback("static_captions")
    log_info("captions", "Using static caption fallback")
    return _static_captions(fallback_text, audio_duration), "static"


def _try_whisper(audio_path: Path) -> list[CaptionWord] | None:
    if audio_path.suffix == ".wav" and "silent" in audio_path.stem:
        return None
    try:
        from faster_whisper import WhisperModel

        model_size = "tiny"
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(str(audio_path), word_timestamps=True)
        words: list[CaptionWord] = []
        for segment in segments:
            if segment.words:
                for w in segment.words:
                    words.append(
                        CaptionWord(
                            word=w.word.strip(),
                            start=w.start,
                            end=w.end,
                        )
                    )
        return words if words else None
    except ImportError:
        log_info("captions", "faster-whisper not installed")
        return None
    except Exception as exc:
        log_error("captions", "faster-whisper failed", exc)
        return None


def _static_captions(text: str, duration: float) -> list[CaptionWord]:
    tokens = text.split()
    if not tokens:
        return []
    step = duration / len(tokens)
    words: list[CaptionWord] = []
    for i, token in enumerate(tokens):
        start = i * step
        end = min(duration, (i + 1) * step)
        words.append(CaptionWord(word=token, start=start, end=end))
    return words


def captions_for_display(words: list[CaptionWord], time: float, window: int = 4) -> str:
    """Return caption text visible at given timestamp."""
    active = [w.word for w in words if w.start <= time < w.end]
    if active:
        return " ".join(active)
    recent = [w.word for w in words if w.start <= time < w.start + 2.0][-window:]
    return " ".join(recent) if recent else ""
