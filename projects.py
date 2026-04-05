"""Текущий проект пользователя и корень для инструментов работы с файлами."""

from __future__ import annotations

from pathlib import Path

from telegram.ext import ContextTypes

from config import PROJECTS, TOOLS_ROOT

SELECTED_PROJECT_KEY = "selected_project"


def effective_tools_root(context: ContextTypes.DEFAULT_TYPE) -> Path:
    """Корень для list/read/write: папка выбранного проекта или TOOLS_ROOT."""
    name = context.user_data.get(SELECTED_PROJECT_KEY)
    if isinstance(name, str) and name in PROJECTS:
        return Path(PROJECTS[name]).resolve()
    return Path(TOOLS_ROOT).resolve()
