"""Central error logging for Shorts Factory Bot (Stage 9)."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

LOG_DIR = Path("logs")
ERROR_LOG = LOG_DIR / "errors.log"

_fallbacks_used: list[str] = []


def setup_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger("shorts_factory")
    if root.handlers:
        return
    root.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    fh = logging.FileHandler(ERROR_LOG, encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(fh)
    root.addHandler(sh)


def log_error(stage: str, message: str, exc: Exception | None = None) -> None:
    setup_logging()
    logger = logging.getLogger("shorts_factory")
    detail = f"[{stage}] {message}"
    if exc:
        detail += f" | {type(exc).__name__}: {exc}"
    logger.error(detail)
    ts = datetime.now(timezone.utc).isoformat()
    with ERROR_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts} [{stage}] {message}")
        if exc:
            f.write(f" | {type(exc).__name__}: {exc}")
        f.write("\n")


def log_info(stage: str, message: str) -> None:
    setup_logging()
    logging.getLogger("shorts_factory").info(f"[{stage}] {message}")


def record_fallback(name: str) -> None:
    if name not in _fallbacks_used:
        _fallbacks_used.append(name)


def get_fallbacks() -> list[str]:
    return list(_fallbacks_used)


def clear_fallbacks() -> None:
    _fallbacks_used.clear()
