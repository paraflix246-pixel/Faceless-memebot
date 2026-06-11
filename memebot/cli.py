"""Command-line interface."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from memebot import __version__
from memebot.config import get_settings
from memebot.logging_setup import setup_logging
from memebot.generator.pipeline import export_video_for_path, generate_batch
from memebot.scheduler.cron import start_scheduler
from memebot.trends.aggregator import fetch_topics

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="memebot",
        description="Faceless Memebot — automated meme pipeline for social channels",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="Generate meme images from trending topics")
    gen.add_argument(
        "-n",
        "--count",
        type=int,
        default=None,
        help="Number of memes to generate (default: BATCH_SIZE from env)",
    )
    gen.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output directory override",
    )
    gen.add_argument(
        "--video",
        action="store_true",
        help="Also export 9:16 MP4 with Ken Burns zoom (requires moviepy)",
    )
    gen.add_argument(
        "--llm",
        action="store_true",
        help="Force LLM captions (requires OPENAI_API_KEY or ANTHROPIC_API_KEY)",
    )

    video = sub.add_parser("video", help="Convert existing PNG memes to MP4")
    video.add_argument(
        "paths",
        nargs="*",
        help="PNG paths (default: all PNGs in output dir)",
    )
    video.add_argument(
        "-o",
        "--output",
        type=str,
        default=None,
        help="Output directory override for source PNGs",
    )

    trends = sub.add_parser("trends", help="List trending topics without generating memes")
    trends.add_argument("-n", "--limit", type=int, default=10, help="Max topics to fetch")

    sched = sub.add_parser("schedule", help="Run meme generation on a cron schedule")
    sched.add_argument(
        "--cron",
        type=str,
        default="0 9 * * *",
        help='Cron expression (default: "0 9 * * *" = daily at 9:00 UTC)',
    )
    sched.add_argument(
        "--run-now",
        action="store_true",
        help="Generate one batch immediately, then start scheduler",
    )

    sub.add_parser("templates", help="List built-in and custom meme templates")

    post = sub.add_parser("post", help="Post memes to social platforms")
    post.add_argument(
        "--platform",
        type=str,
        required=True,
        help="Platform: x, instagram, tiktok, youtube",
    )
    post.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Log what would be posted (default)",
    )
    post.add_argument(
        "--live",
        action="store_true",
        help="Actually post when credentials are configured",
    )
    post.add_argument(
        "--latest",
        action="store_true",
        help="Use the newest meme in output/",
    )
    post.add_argument(
        "--image",
        type=str,
        default=None,
        help="Specific PNG path to post",
    )
    post.add_argument(
        "--caption",
        type=str,
        default=None,
        help="Override caption text",
    )

    sub.add_parser("review", help="Launch Streamlit batch review UI")

    return parser


def cmd_generate(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.output:
        settings.output_dir = Path(args.output)

    try:
        memes = generate_batch(
            settings,
            count=args.count,
            force_llm=args.llm,
            export_video=args.video,
        )
    except ValueError as exc:
        logger.error("%s", exc)
        return 1

    if not memes:
        logger.error("No memes were generated")
        return 1

    print(f"\nGenerated {len(memes)} meme(s) in {settings.output_dir}:\n")
    for meme in memes:
        print(f"  {meme.image_path.name}")
        if meme.video_path:
            print(f"    video:    {meme.video_path.name}")
        print(f"    template: {meme.template}")
        title_preview = meme.topic.title if len(meme.topic.title) <= 70 else meme.topic.title[:70] + "..."
        print(f"    topic:    {title_preview}")
        print(f"    captions: {' / '.join(meme.captions)}")
        print()
    return 0


def cmd_video(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.output:
        settings.output_dir = Path(args.output)

    paths = [Path(p) for p in args.paths] if args.paths else sorted(settings.output_dir.glob("*.png"))
    if not paths:
        logger.error("No PNG files found")
        return 1

    from memebot.generator.video import moviepy_status

    ok, err = moviepy_status()
    if not ok:
        logger.error("moviepy not installed: %s", err)
        logger.error("Install with: pip install moviepy")
        return 1

    exported = 0
    for png in paths:
        try:
            out = export_video_for_path(png, settings)
            print(f"  {out.name}")
            exported += 1
        except Exception as exc:
            logger.error("Failed %s: %s", png.name, exc)

    print(f"\nExported {exported} video(s)\n")
    return 0 if exported else 1


def cmd_trends(args: argparse.Namespace) -> int:
    settings = get_settings()
    topics = fetch_topics(settings, limit=args.limit)
    print(f"\nTop {len(topics)} topics:\n")
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. [{topic.source}] (score={topic.score})")
        print(f"     {topic.title}")
        if topic.url:
            print(f"     {topic.url}")
        print()
    return 0


def cmd_schedule(args: argparse.Namespace) -> int:
    settings = get_settings()
    if args.run_now:
        memes = generate_batch(settings)
        print(f"Initial batch: {len(memes)} meme(s) -> {settings.output_dir}")
    start_scheduler(settings, cron=args.cron)
    return 0


def cmd_templates(_args: argparse.Namespace) -> int:
    from memebot.templates.custom import list_all_templates

    builtin, custom = list_all_templates()
    print("\nBuilt-in meme templates:\n")
    for name in builtin:
        print(f"  • {name}")

    print("\nCustom templates (assets/templates/):\n")
    if custom:
        for name, path in custom:
            print(f"  • {name}  ←  {path.name}")
    else:
        print("  (none — drop PNG/JPG files into assets/templates/)")

    print("\nTemplates are chosen randomly per meme. Portrait 1080×1920 (9:16).\n")
    return 0


def cmd_post(args: argparse.Namespace) -> int:
    from memebot.posting.runner import post_to_platform

    settings = get_settings()
    dry_run = not args.live

    try:
        result = post_to_platform(
            args.platform,
            settings,
            image_path=Path(args.image) if args.image else None,
            caption=args.caption,
            dry_run=dry_run,
            use_latest=args.latest or args.image is None,
        )
    except Exception as exc:
        logger.error("%s", exc)
        return 1

    mode = "DRY-RUN" if result.dry_run else "LIVE"
    status = "OK" if result.success else "FAILED"
    print(f"\n[{mode}] {result.platform}: {status}")
    print(f"  {result.message}\n")
    return 0 if result.success else 1


def cmd_review(_args: argparse.Namespace) -> int:
    import subprocess

    app_path = Path(__file__).resolve().parent / "review" / "app.py"
    if not app_path.exists():
        logger.error("Review app not found at %s", app_path)
        return 1

    print("Launching Streamlit review UI...")
    print("Press Ctrl+C to stop.\n")
    try:
        subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            check=False,
        )
    except KeyboardInterrupt:
        pass
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    settings = get_settings()
    setup_logging(settings.log_level)

    handlers = {
        "generate": cmd_generate,
        "video": cmd_video,
        "trends": cmd_trends,
        "schedule": cmd_schedule,
        "templates": cmd_templates,
        "post": cmd_post,
        "review": cmd_review,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
