from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

import ollama

from auth import require_allowed_user
from config import INCLUDE_THINKING
from ollama_helper import format_completion_models_list, get_completion_models
from ollama_state import OLLAMA_MESSAGES_KEY, OLLAMA_MODEL_KEY, effective_messages, effective_model


@require_allowed_user
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет, я бот для общения с моделью Ollama.")


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
        "/message_count — сколько сообщений в истории диалога\n\n"
        "Любое текстовое сообщение (не команда) отправляется в модель как продолжение диалога."
    )


@require_allowed_user
async def cmd_new_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[OLLAMA_MESSAGES_KEY] = []
    await update.message.reply_text("История диалога сброшена.")


@require_allowed_user
async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id,
        action=ChatAction.TYPING,
    )
    effective_messages(context).append(ollama.Message(role="user", content=update.message.text))
    response = ollama.chat(model=effective_model(context), messages=effective_messages(context))
    if INCLUDE_THINKING and response.message.thinking:
        await update.message.reply_markdown(
            f"Thinking:\n{response.message.thinking}\n\nContent:\n{response.message.content}"
        )
    else:
        await update.message.reply_markdown(response.message.content)
    effective_messages(context).append(response.message)


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

