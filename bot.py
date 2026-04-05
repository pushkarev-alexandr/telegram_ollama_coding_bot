from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from config import PROXY_URL, TELEGRAM_BOT_TOKEN
from handlers import (
    CALLBACK_TOOL_NO,
    CALLBACK_TOOL_YES,
    chat,
    cmd_get_model,
    cmd_help,
    cmd_list_models,
    cmd_message_count,
    cmd_new_chat,
    cmd_set_model,
    cmd_start,
    tool_permission_callback,
)


def main() -> None:
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).proxy(PROXY_URL).get_updates_proxy(PROXY_URL).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("new_chat", cmd_new_chat))
    app.add_handler(CommandHandler("get_model", cmd_get_model))
    app.add_handler(CommandHandler("set_model", cmd_set_model))
    app.add_handler(CommandHandler("list_models", cmd_list_models))
    app.add_handler(CommandHandler("message_count", cmd_message_count))
    app.add_handler(
        CallbackQueryHandler(
            tool_permission_callback,
            pattern=f"^({CALLBACK_TOOL_YES}|{CALLBACK_TOOL_NO})$",
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))
    print("Бот запущен, нажмите Ctrl+C для выхода")
    app.run_polling()


if __name__ == "__main__":
    main()
