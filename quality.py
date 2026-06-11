"""Stage 7: Quality checks — duration, sync, scene count."""

from __future__ import annotations

from pathlib import Path

from pipeline_log import log_info, log_error
from scenes import Scene


MIN_DURATION = 25.0
TARGET_MIN = 30.0
TARGET_MAX = 60.0


def get_audio_duration(audio_path: Path) -> float:
    try:
        from moviepy import AudioFileClip

        clip = AudioFileClip(str(audio_path))
        dur = clip.duration
        clip.close()
        return dur
    except Exception:
        pass
    try:
        import wave

        with wave.open(str(audio_path), "r") as wf:
            return wf.getnframes() / float(wf.getframerate())
    except Exception:
        return 0.0


def get_video_duration(video_path: Path) -> float:
    try:
        from moviepy import VideoFileClip

        clip = VideoFileClip(str(video_path))
        dur = clip.duration
        clip.close()
        return dur
    except Exception as exc:
        log_error("quality", "Could not read video duration", exc)
        return 0.0


def check_scenes(scenes: list[Scene]) -> tuple[bool, str]:
    if len(scenes) < 3:
        return False, f"Too few scenes: {len(scenes)} (need >= 3)"
    if len(scenes) > 10:
        return False, f"Too many scenes: {len(scenes)} (max 10)"
    return True, "OK"


def estimate_video_duration(scenes: list[Scene]) -> float:
    return sum(s.duration for s in scenes)


def needs_longer_script(video_duration: float, audio_duration: float) -> bool:
    effective = max(video_duration, audio_duration)
    return effective < MIN_DURATION


def adjust_scene_durations(scenes: list[Scene], target: float = 45.0) -> None:
    """Stretch scene durations to reach target total."""
    current = sum(s.duration for s in scenes)
    if current >= target:
        return
    factor = target / max(current, 1.0)
    for scene in scenes:
        scene.duration = min(10.0, scene.duration * factor)
    remaining = target - sum(s.duration for s in scenes)
    if remaining > 0 and scenes:
        scenes[-1].duration += remaining


def quality_report(
    video_path: Path,
    scenes: list[Scene],
    audio_duration: float,
) -> dict:
    video_dur = get_video_duration(video_path)
    ok_scenes, scene_msg = check_scenes(scenes)
    sync_ok = abs(video_dur - audio_duration) < 5.0 or video_dur >= audio_duration - 1.0
    report = {
        "video_duration": video_dur,
        "audio_duration": audio_duration,
        "scene_count": len(scenes),
        "scenes_ok": ok_scenes,
        "scene_message": scene_msg,
        "sync_ok": sync_ok,
        "duration_ok": TARGET_MIN <= video_dur <= TARGET_MAX,
    }
    log_info(
        "quality",
        f"duration={video_dur:.1f}s audio={audio_duration:.1f}s scenes={len(scenes)} sync={sync_ok}",
    )
    return report
