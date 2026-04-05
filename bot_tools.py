"""Инструменты для Ollama: определения и выполнение (после подтверждения пользователем)."""

from __future__ import annotations

import json
from pathlib import Path

MAX_READ_BYTES = 1_048_576  # 1 MiB


def _safe_path_under_root(user_path: str, root: Path) -> Path:
    root_resolved = root.resolve()
    candidate = (root_resolved / user_path).resolve()
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"Путь вне разрешённого корня ({root_resolved}): {user_path!r}"
        ) from exc
    return candidate


def list_directory_contents(path: str, root: Path) -> dict:
    """
    Возвращает список имён подпапок и файлов в указанной папке внутри root.

    Args:
        path: Относительный путь от корня просмотра (например «.» или «src»).
        root: Абсолютный корень (папка проекта или TOOLS_ROOT).
    """
    target = _safe_path_under_root(path, root)
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


def read_file_text(path: str, root: Path) -> dict:
    """Читает текстовый файл UTF-8 внутри root."""
    target = _safe_path_under_root(path, root)
    if not target.exists():
        return {"error": f"Файл не существует: {path}"}
    if not target.is_file():
        return {"error": f"Не является файлом: {path}"}
    try:
        size = target.stat().st_size
        if size > MAX_READ_BYTES:
            return {
                "error": (
                    f"Файл слишком большой ({size} байт), лимит {MAX_READ_BYTES} байт."
                )
            }
        content = target.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"error": str(e)}
    return {"path": str(target), "content": content}


def write_file_text(path: str, content: str, root: Path) -> dict:
    """Записывает текст в файл UTF-8; родительские папки создаются при необходимости."""
    target = _safe_path_under_root(path, root)
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8", newline="")
    except OSError as e:
        return {"error": str(e)}
    return {"path": str(target), "written": True, "bytes": len(content.encode("utf-8"))}


def create_directory(path: str, root: Path) -> dict:
    """Создаёт папку (и при необходимости родительские) внутри root."""
    target = _safe_path_under_root(path, root)
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return {"error": str(e)}
    return {"path": str(target), "created": True}


def execute_tool(name: str, arguments: dict, root: Path) -> str:
    """Выполняет известный инструмент; результат — JSON-строка для role=tool."""
    if name == "list_directory_contents":
        raw_path = arguments.get("path", ".")
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)
        result = list_directory_contents(raw_path, root)
        return json.dumps(result, ensure_ascii=False)

    if name == "read_file_text":
        raw_path = arguments.get("path", "")
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)
        result = read_file_text(raw_path, root)
        return json.dumps(result, ensure_ascii=False)

    if name == "write_file_text":
        raw_path = arguments.get("path", "")
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)
        content = arguments.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        result = write_file_text(raw_path, content, root)
        return json.dumps(result, ensure_ascii=False)

    if name == "create_directory":
        raw_path = arguments.get("path", "")
        if not isinstance(raw_path, str):
            raw_path = str(raw_path)
        result = create_directory(raw_path, root)
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
                "внутри корня текущего проекта (или общего корня, если проект не выбран). "
                "Путь задаётся относительно этого корня. Текущая корневая папка — «.»."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": (
                            "Относительный путь к папке от корня проекта, например «.» или «subfolder»."
                        ),
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file_text",
            "description": (
                "Читает содержимое текстового файла (UTF-8) по относительному пути от корня текущего проекта."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Относительный путь к файлу, например «src/main.py».",
                    },
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_text",
            "description": (
                "Записывает текст в файл (UTF-8) по относительному пути; при необходимости создаёт недостающие папки."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Относительный путь к файлу.",
                    },
                    "content": {
                        "type": "string",
                        "description": "Полное содержимое файла.",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_directory",
            "description": (
                "Создаёт папку по относительному пути от корня текущего проекта (включая родительские при необходимости)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Относительный путь создаваемой папки.",
                    },
                },
                "required": ["path"],
            },
        },
    },
]
