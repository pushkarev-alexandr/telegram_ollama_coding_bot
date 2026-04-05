from telegram import Update
from telegram.error import BadRequest


async def reply_markdown_or_plain(update: Update, text: str) -> None:
    """Markdown v1 строгий; ответы модели часто ломают разбор — тогда шлём как обычный текст."""
    msg = update.effective_message
    if not msg:
        return
    try:
        await msg.reply_markdown(text)
    except BadRequest as exc:
        if "parse entities" in str(exc).lower():
            await msg.reply_text(text)
        else:
            raise
