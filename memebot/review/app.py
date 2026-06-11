"""Streamlit batch review UI for generated memes."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import streamlit as st

from memebot.config import get_settings


def _load_pending_memes(output_dir: Path) -> list[dict]:
    """Load PNG+JSON pairs not yet in approved/."""
    approved_dir = output_dir / "approved"
    pending: list[dict] = []

    for png in sorted(output_dir.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True):
        if approved_dir.exists() and (approved_dir / png.name).exists():
            continue
        meta_path = png.with_suffix(".json")
        metadata = {}
        if meta_path.exists():
            try:
                metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {"error": "Invalid JSON"}

        video = png.with_suffix(".mp4")
        pending.append(
            {
                "png": png,
                "json": meta_path if meta_path.exists() else None,
                "video": video if video.exists() else None,
                "metadata": metadata,
            }
        )
    return pending


def _approve_meme(item: dict, approved_dir: Path) -> None:
    approved_dir.mkdir(parents=True, exist_ok=True)
    for key in ("png", "json", "video"):
        src = item.get(key)
        if src and Path(src).exists():
            shutil.copy2(src, approved_dir / Path(src).name)


def _reject_meme(item: dict, rejected_dir: Path) -> None:
    rejected_dir.mkdir(parents=True, exist_ok=True)
    for key in ("png", "json", "video"):
        src = item.get(key)
        if src and Path(src).exists():
            dest = rejected_dir / Path(src).name
            shutil.move(str(src), str(dest))


def main() -> None:
    st.set_page_config(page_title="Memebot Review", page_icon="🎭", layout="wide")
    st.title("Faceless Memebot — Batch Review")

    settings = get_settings()
    output_dir = settings.output_dir
    approved_dir = settings.approved_dir
    rejected_dir = output_dir / "rejected"

    st.caption(f"Output: `{output_dir}` · Approved: `{approved_dir}`")

    pending = _load_pending_memes(output_dir)
    if not pending:
        st.info("No pending memes to review. Run `python -m memebot generate` first.")
        return

    st.write(f"**{len(pending)}** meme(s) pending review")

    for idx, item in enumerate(pending):
        png: Path = item["png"]
        metadata = item["metadata"]

        with st.container(border=True):
            col_img, col_meta = st.columns([1, 1])

            with col_img:
                st.image(str(png), caption=png.name, use_container_width=True)
                if item["video"]:
                    st.video(str(item["video"]))

            with col_meta:
                st.subheader(metadata.get("template", "unknown template"))
                topic = metadata.get("topic", {})
                st.write(f"**Topic:** {topic.get('title', '—')}")
                st.write(f"**Source:** {topic.get('source', '—')}")
                captions = metadata.get("captions", [])
                if captions:
                    st.write("**Captions:**")
                    for cap in captions:
                        st.write(f"- {cap}")
                with st.expander("Full metadata JSON"):
                    st.json(metadata)

            c1, c2, _ = st.columns([1, 1, 4])
            with c1:
                if st.button("Approve", key=f"approve_{idx}_{png.name}"):
                    _approve_meme(item, approved_dir)
                    st.success(f"Approved → {approved_dir.name}/")
                    st.rerun()
            with c2:
                if st.button("Reject", key=f"reject_{idx}_{png.name}"):
                    _reject_meme(item, rejected_dir)
                    st.warning(f"Rejected → {rejected_dir.name}/")
                    st.rerun()


if __name__ == "__main__":
    main()
