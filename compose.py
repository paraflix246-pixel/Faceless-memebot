"""Stage 6+8: Video composition and MP4 export."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from captions import CaptionWord, captions_for_display
from pipeline_log import log_error, log_info, record_fallback
from scenes import Scene

WIDTH = 1080
HEIGHT = 1920
FPS = 30
ZOOM_END = 1.15


def compose_video(
    scenes: list[Scene],
    image_paths: list[Path],
    audio_path: Path,
    captions: list[CaptionWord],
    output_path: Path,
    *,
    truncate_audio: bool = False,
    video_duration: float | None = None,
) -> Path:
    """Build final MP4 with Ken Burns, captions, and voiceover."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _compose_moviepy(
            scenes,
            image_paths,
            audio_path,
            captions,
            output_path,
            truncate_audio=truncate_audio,
            video_duration=video_duration,
        )
    except Exception as exc:
        log_error("compose", "MoviePy composition failed", exc)
        record_fallback("ffmpeg_compose")
        return _compose_ffmpeg_fallback(
            scenes, image_paths, audio_path, output_path, video_duration=video_duration
        )


def _compose_moviepy(
    scenes: list[Scene],
    image_paths: list[Path],
    audio_path: Path,
    captions: list[CaptionWord],
    output_path: Path,
    *,
    truncate_audio: bool = False,
    video_duration: float | None = None,
) -> Path:
    from moviepy import AudioFileClip, CompositeVideoClip, ImageClip, VideoClip, concatenate_videoclips

    total_duration = video_duration or max(sum(s.duration for s in scenes), 30.0)

    scene_clips = []
    for scene, img_path in zip(scenes, image_paths):
        prepared = _fit_cover(Image.open(img_path).convert("RGB"), WIDTH, HEIGHT)
        tmp = img_path.parent / f"{img_path.stem}_cover.png"
        prepared.save(tmp)

        dur = scene.duration
        clip = ImageClip(str(tmp), duration=dur)

        def zoom(t: float, d: float = dur) -> float:
            progress = t / d if d else 0.0
            return 1.0 + (ZOOM_END - 1.0) * progress

        zoomed = clip.resized(zoom)
        scene_clips.append(zoomed)

    video = concatenate_videoclips(scene_clips, method="compose")
    if video.duration < total_duration:
        total_duration = video.duration

    caption_clip = _make_caption_clip(captions, video.duration)
    if caption_clip is not None:
        video = CompositeVideoClip([video, caption_clip], size=(WIDTH, HEIGHT))

    audio = AudioFileClip(str(audio_path))
    if truncate_audio or audio.duration > video.duration:
        audio = audio.subclipped(0, video.duration)
    elif audio.duration > video.duration * 0.9:
        video = video.with_duration(min(audio.duration, total_duration))

    final_duration = min(video.duration, audio.duration) if audio.duration else video.duration
    video = video.with_duration(final_duration).with_audio(audio.subclipped(0, final_duration))

    video.write_videofile(
        str(output_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        logger=None,
    )
    video.close()
    audio.close()
    for c in scene_clips:
        c.close()
    log_info("compose", f"Exported {output_path.name} ({final_duration:.1f}s)")
    return output_path


def _make_caption_clip(captions: list[CaptionWord], duration: float):
    from moviepy import VideoClip

    def make_frame(t: float) -> np.ndarray:
        text = captions_for_display(captions, t, window=5)
        return _render_caption_bar(text)

    clip = VideoClip(make_frame, duration=duration)
    return clip.with_position(("center", HEIGHT - 280))


def _fit_cover(img: Image.Image, tw: int, th: int) -> Image.Image:
    iw, ih = img.size
    scale = max(tw / iw, th / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    resized = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - tw) // 2
    top = (nh - th) // 2
    return resized.crop((left, top, left + tw, top + th))


def _render_caption_bar(text: str) -> np.ndarray:
    bar = Image.new("RGBA", (WIDTH, 120), (0, 0, 0, 0))
    if not text:
        return np.array(Image.new("RGB", (WIDTH, 120), (0, 0, 0)))
    draw = ImageDraw.Draw(bar)
    font = _caption_font(42)
    margin = 40
    max_w = WIDTH - 2 * margin
    lines = _wrap(text.upper(), font, max_w, draw)
    line_h = draw.textbbox((0, 0), "Ay", font=font)[3] + 6
    total_h = len(lines) * line_h
    y = (120 - total_h) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (WIDTH - w) // 2
        for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2)]:
            draw.text((x + dx, y + dy), line, fill=(0, 0, 0, 255), font=font)
        draw.text((x, y), line, fill=(255, 255, 0, 255), font=font)
        y += line_h
    rgb = Image.new("RGB", (WIDTH, 120), (0, 0, 0))
    rgb.paste(bar, mask=bar.split()[3] if bar.mode == "RGBA" else None)
    return np.array(rgb)


def _caption_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in (
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/impact.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, max_w: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = text.split()
    lines: list[str] = []
    cur: list[str] = []
    for word in words:
        test = " ".join(cur + [word])
        if draw.textbbox((0, 0), test, font=font)[2] <= max_w:
            cur.append(word)
        else:
            if cur:
                lines.append(" ".join(cur))
            cur = [word]
    if cur:
        lines.append(" ".join(cur))
    return lines[:2]


def _compose_ffmpeg_fallback(
    scenes: list[Scene],
    image_paths: list[Path],
    audio_path: Path,
    output_path: Path,
    video_duration: float | None = None,
) -> Path:
    import subprocess
    import tempfile

    tmp = Path(tempfile.mkdtemp())
    list_file = tmp / "concat.txt"
    segment_paths: list[Path] = []

    for scene, img in zip(scenes, image_paths):
        seg = tmp / f"seg_{scene.id}.mp4"
        dur = scene.duration
        subprocess.run(
            [
                "ffmpeg", "-y", "-loop", "1", "-i", str(img),
                "-c:v", "libx264", "-t", str(dur),
                "-pix_fmt", "yuv420p", "-vf", f"scale={WIDTH}:{HEIGHT}",
                str(seg),
            ],
            check=True,
            capture_output=True,
        )
        segment_paths.append(seg)

    with list_file.open("w") as f:
        for seg in segment_paths:
            f.write(f"file '{seg.as_posix()}'\n")

    silent_video = tmp / "video.mp4"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(silent_video)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(silent_video), "-i", str(audio_path),
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(output_path),
        ],
        check=True,
        capture_output=True,
    )
    log_info("compose", f"FFmpeg fallback exported {output_path.name}")
    return output_path
