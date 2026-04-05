from telegram.ext import ContextTypes

import ollama

from config import DEFAULT_MODEL
from ollama_helper import get_least_params_model, is_valid_completion_model

OLLAMA_MESSAGES_KEY = "ollama_messages"
OLLAMA_MODEL_KEY = "ollama_model"
# Ожидание ответа по inline-кнопкам для вызова инструмента моделью
PENDING_TOOLS_KEY = "pending_tools"
# Счётчик вызовов ollama.chat за один ответ пользователя (лимит цепочки tool → модель)
OLLAMA_INVOKE_IN_TURN_KEY = "ollama_invoke_in_turn"


def effective_model(context: ContextTypes.DEFAULT_TYPE) -> str:
    user_model = context.user_data.get(OLLAMA_MODEL_KEY)
    if not user_model:
        print(f"выбираем модель по умолчанию {DEFAULT_MODEL}")
        user_model = DEFAULT_MODEL
    if not is_valid_completion_model(user_model):
        print(f"Модель {user_model} не доступна, выбираем модель с наименьшим числом параметров")
        user_model = get_least_params_model()
        print(f"Выбрана модель {user_model}")
    context.user_data[OLLAMA_MODEL_KEY] = user_model
    return user_model


def effective_messages(context: ContextTypes.DEFAULT_TYPE) -> list[ollama.Message]:
    messages = context.user_data.get(OLLAMA_MESSAGES_KEY)
    if not messages:
        messages = []
        context.user_data[OLLAMA_MESSAGES_KEY] = messages
    return messages
