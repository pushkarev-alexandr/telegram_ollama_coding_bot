from collections.abc import Awaitable, Callable
from functools import wraps

from config import ALLOWED_USER_IDS
from telegram import Update
from telegram.ext import ContextTypes

DENIED = "У вас нет доступа к боту."


def require_allowed_user(
    handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    """Логирует текст сообщения в консоль и пропускает только разрешённых пользователей."""

    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        msg = update.effective_message
        if msg and msg.text is not None:
            print(msg.text)
        u = update.effective_user
        if not u or u.id not in ALLOWED_USER_IDS:
            await update.effective_message.reply_text(DENIED)
            return
        await handler(update, context)

    return wrapped


def require_allowed_callback(
    handler: Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]],
) -> Callable[[Update, ContextTypes.DEFAULT_TYPE], Awaitable[None]]:
    """Как require_allowed_user, но для callback_query (нажатия кнопок)."""

    @wraps(handler)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        u = update.effective_user
        q = update.callback_query
        if not u or u.id not in ALLOWED_USER_IDS:
            if q:
                await q.answer("У вас нет доступа к боту.", show_alert=True)
            return
        await handler(update, context)

    return wrapped
