import json
from pathlib import Path
from typing import Any

import ollama
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from auth import require_allowed_callback, require_allowed_user
from bot_tools import OLLAMA_TOOLS, execute_tool
from config import INCLUDE_THINKING, PROJECTS
from projects import SELECTED_PROJECT_KEY, effective_tools_root
from ollama_helper import format_completion_models_list, get_completion_models
from ollama_state import (
    OLLAMA_INVOKE_IN_TURN_KEY,
    OLLAMA_MESSAGES_KEY,
    OLLAMA_MODEL_KEY,
    PENDING_TOOLS_KEY,
    effective_messages,
    effective_model,
)
from telegram_reply import reply_markdown_or_plain

MAX_TOOL_ROUNDS = 15

CALLBACK_TOOL_YES = "tool_yes"
CALLBACK_TOOL_NO = "tool_no"


def _tool_calls_payload(message: ollama.Message) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for tc in message.tool_calls or []:
        fn = tc.function
        out.append(
            {
                "name": fn.name,
                "arguments": dict(fn.arguments),
            }
        )
    return out


def _format_tool_prompt(name: str, arguments: dict[str, Any]) -> str:
    args_text = json.dumps(arguments, ensure_ascii=False, indent=2)
    return (
        "Модель запросила выполнение функции.\n\n"
        f"Имя функции: {name}\n\n"
        f"Аргументы:\n```json\n{args_text}\n```\n\n"
        "Разрешить выполнение?"
    )


async def _send_tool_permission_request(
    update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, arguments: dict[str, Any]
) -> None:
    text = _format_tool_prompt(name, arguments)
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Разрешить", callback_data=CALLBACK_TOOL_YES),
                InlineKeyboardButton("Отклонить", callback_data=CALLBACK_TOOL_NO),
            ]
        ]
    )
    msg = update.effective_message
    if msg:
        await msg.reply_text(text, reply_markup=kb)


async def _reply_final_assistant(
    update: Update, message: ollama.Message
) -> None:
    if INCLUDE_THINKING and message.thinking:
        text = f"Thinking:\n{message.thinking}\n\nContent:\n{message.content or ''}"
    else:
        text = message.content or ""
    await reply_markdown_or_plain(update, text)


async def _run_ollama_after_tools_resolved(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """После добавления всех tool-сообщений — следующий вызов модели (возможны новые tool_calls)."""
    n = context.user_data.get(OLLAMA_INVOKE_IN_TURN_KEY, 0) + 1
    context.user_data[OLLAMA_INVOKE_IN_TURN_KEY] = n
    if n > MAX_TOOL_ROUNDS:
        em = update.effective_message
        if em:
            await em.reply_text(
                "Достигнут лимит вызовов модели с инструментами в этом ответе."
            )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )
    response = ollama.chat(
        model=effective_model(context),
        messages=effective_messages(context),
        tools=OLLAMA_TOOLS,
    )
    assistant = response.message
    effective_messages(context).append(assistant)

    if not assistant.tool_calls:
        await _reply_final_assistant(update, assistant)
        return

    calls = _tool_calls_payload(assistant)
    context.user_data[PENDING_TOOLS_KEY] = {
        "calls": calls,
        "index": 0,
    }
    if assistant.content:
        await reply_markdown_or_plain(update, assistant.content)
    first = calls[0]
    await _send_tool_permission_request(
        update, context, first["name"], first["arguments"]
    )


@require_allowed_user
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get(PENDING_TOOLS_KEY):
        await update.message.reply_text(
            "Сначала ответьте на запрос разрешения инструмента (кнопки в сообщении выше)."
        )
        return

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )
    context.user_data[OLLAMA_INVOKE_IN_TURN_KEY] = 0
    effective_messages(context).append(
        ollama.Message(role="user", content=update.message.text)
    )
    await _run_ollama_after_tools_resolved(update, context)


@require_allowed_callback
async def tool_permission_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    query = update.callback_query
    await query.answer()
    pending = context.user_data.get(PENDING_TOOLS_KEY)
    if not pending:
        await query.edit_message_reply_markup(reply_markup=None)
        return

    calls: list[dict[str, Any]] = pending["calls"]
    idx: int = pending["index"]
    if idx >= len(calls):
        context.user_data[PENDING_TOOLS_KEY] = None
        await query.edit_message_reply_markup(reply_markup=None)
        return

    current = calls[idx]
    name = current["name"]
    arguments = current["arguments"]

    approved = query.data == CALLBACK_TOOL_YES
    if approved:
        try:
            content = execute_tool(name, arguments, effective_tools_root(context))
        except Exception as exc:
            content = json.dumps({"error": str(exc)}, ensure_ascii=False)
    else:
        content = json.dumps(
            {
                "denied": True,
                "message": "Пользователь отклонил выполнение этой функции.",
            },
            ensure_ascii=False,
        )

    effective_messages(context).append(
        ollama.Message(role="tool", content=content, tool_name=name)
    )
    idx += 1
    pending["index"] = idx

    await query.edit_message_reply_markup(reply_markup=None)

    if idx < len(calls):
        nxt = calls[idx]
        await _send_tool_permission_request(
            update, context, nxt["name"], nxt["arguments"]
        )
        return

    context.user_data[PENDING_TOOLS_KEY] = None
    await _run_ollama_after_tools_resolved(update, context)


@require_allowed_user
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет, я бот для общения с моделью Ollama.")


@require_allowed_user
async def cmd_exit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Прощай")
    context.application.stop_running()


@require_allowed_user
async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды:\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/new_chat — сбросить историю диалога с моделью\n"
        "/get_model — показать текущую модель Ollama\n"
        "/set_model <имя> — выбрать локальную модель\n"
        "/list_models — список доступных локальных моделей\n"
        "/message_count — сколько сообщений в истории диалога\n"
        "/list_projects — список настроенных проектов и текущий выбор\n"
        "/set_project <имя> — работать с файлами в папке этого проекта\n"
        "/clear_project — сбросить выбор проекта (корень по умолчанию)\n"
        "/exit — остановить бота и завершить программу\n\n"
        "Любое текстовое сообщение (не команда) отправляется в модель как продолжение диалога.\n\n"
        "Если модель вызывает инструмент (список файлов, чтение/запись файла и т.д.), бот спросит у вас "
        "разрешение и покажет имя функции и аргументы. Пути в инструментах задаются относительно папки "
        "текущего проекта (см. /set_project)."
    )


@require_allowed_user
async def cmd_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[OLLAMA_MESSAGES_KEY] = []
    context.user_data[PENDING_TOOLS_KEY] = None
    context.user_data[OLLAMA_INVOKE_IN_TURN_KEY] = 0
    await update.message.reply_text("История диалога сброшена.")


@require_allowed_user
async def cmd_get_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Текущая модель: {effective_model(context)}")


@require_allowed_user
async def cmd_list_models(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(format_completion_models_list())


@require_allowed_user
async def cmd_message_count(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    n = len(context.user_data.get(OLLAMA_MESSAGES_KEY, []))
    await update.message.reply_text(f"Сообщений в истории диалога: {n}")


@require_allowed_user
async def cmd_set_model(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Укажите имя модели, например:\n/set_model gemma4:26b"
        )
        return
    name = " ".join(context.args).strip()
    models = get_completion_models()
    if name not in models:
        await update.message.reply_text(
            f"Модель «{name}» недоступна.\n\n{format_completion_models_list(models)}"
        )
        return
    context.user_data[OLLAMA_MODEL_KEY] = name
    await update.message.reply_text(f"Модель установлена: {name}")


@require_allowed_user
async def cmd_list_projects(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    current = context.user_data.get(SELECTED_PROJECT_KEY)
    root = effective_tools_root(context)
    lines = [
        f"Текущий корень для инструментов: {root}",
        f"Выбранный проект: {current if current else '(не выбран, используется корень по умолчанию)'}",
        "",
        "Проекты из настройки PROJECTS:",
    ]
    if not PROJECTS:
        lines.append("  (словарь PROJECTS пуст — добавьте имена и пути в config.py)")
    else:
        for pname, ppath in sorted(PROJECTS.items()):
            mark = " ← текущий" if pname == current else ""
            lines.append(f"  • {pname} → {ppath}{mark}")
    await update.message.reply_text("\n".join(lines))


@require_allowed_user
async def cmd_set_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Укажите имя проекта из настройки PROJECTS, например:\n"
            "/set_project my_app\n\n"
            "Список проектов: /list_projects\n"
            "Сброс: /clear_project"
        )
        return
    name = " ".join(context.args).strip()
    if name not in PROJECTS:
        await update.message.reply_text(
            f"Проект «{name}» не найден в PROJECTS. См. /list_projects"
        )
        return
    proj_path = Path(PROJECTS[name]).resolve()
    if not proj_path.is_dir():
        await update.message.reply_text(
            f"Папка проекта не существует или не является каталогом:\n{proj_path}"
        )
        return
    context.user_data[SELECTED_PROJECT_KEY] = name
    await update.message.reply_text(f"Активный проект: {name}\nКорень: {proj_path}")


@require_allowed_user
async def cmd_clear_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[SELECTED_PROJECT_KEY] = None
    await update.message.reply_text(
        f"Выбор проекта сброшен. Корень инструментов: {effective_tools_root(context)}"
    )
