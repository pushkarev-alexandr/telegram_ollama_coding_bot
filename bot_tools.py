"""Инструменты для Ollama: определения и выполнение (после подтверждения пользователем)."""

from __future__ import annotations

import json
from pathlib import Path

from config import TOOLS_ROOT


def _safe_path_under_root(user_path: str) -> Path:
    root = Path(TOOLS_ROOT).resolve()
    candidate = (root / user_path).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"Путь вне разрешённого корня ({root}): {user_path!r}"
        ) from exc
    return candidate


def list_directory_contents(path: str) -> dict:
    """
    Возвращает список имён подпапок и файлов в указанной папке внутри TOOLS_ROOT.

    Args:
        path: Относительный путь от корня просмотра (например «.» или «src»).
    """
    target = _safe_path_under_root(path)
    if not target.exists():
        return {"error": f"Путь не существует: {path}", "folders": [], "files": []}
    if not target.is_dir():
        return {"error": f"Не является папкой: {path}", "folders": [], "files": []}
    folders: list[str] = []
    files: list[str] = []
    try:
        for entry in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if entry.is_dir():
                folders.append(entry.name)
            elif entry.is_file():
                files.append(entry.name)
    except OSError as e:
        return {"error": str(e), "folders": [], "files": []}
    return {
        "path": str(target),
        "folders": folders,
        "files": files,
    }


def execute_tool(name: str, arguments: dict) -> str:
    """Выполняет известный инструмент; результат — JSON-строка для role=tool."""
    if name == "list_directory_contents":
        raw_path = arguments.get("path", ".")
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)
        result = list_directory_contents(raw_path)
        return json.dumps(result, ensure_ascii=False)
    return json.dumps(
        {"error": f"Неизвестный инструмент: {name}"}, ensure_ascii=False
    )


OLLAMA_TOOLS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "list_directory_contents",
            "description": (
                "Возвращает список имён подпапок и список имён файлов в указанной папке "
                "внутри разрешённого корня на машине бота. Путь задаётся относительно корня."
                "Текущей папкой является корневая папка, путь к ней указывается как '.'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Относительный путь к папке от корня просмотра, например «.» или «subfolder»."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
    },
]
