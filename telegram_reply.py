from telegram import Update
from telegram.error import BadRequest


async def reply_markdown_or_plain(update: Update, text: str) -> None:
    """Markdown v1 строгий; ответы модели часто ломают разбор — тогда шлём как обычный текст."""
    try:
        await update.message.reply_markdown(text)
    except BadRequest as exc:
        if "parse entities" in str(exc).lower():
            await update.message.reply_text(text)
        else:
            raise
