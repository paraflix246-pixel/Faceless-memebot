"""Meme template registry."""

from __future__ import annotations

import random

from memebot.templates.custom import discover_custom_templates

BUILTIN_TEMPLATES = ["classic", "drake", "two_panel", "expanding_brain", "choice"]


def all_template_names() -> list[str]:
    custom = discover_custom_templates()
    return BUILTIN_TEMPLATES + list(custom.keys())


def pick_template() -> str:
    return random.choice(all_template_names())
