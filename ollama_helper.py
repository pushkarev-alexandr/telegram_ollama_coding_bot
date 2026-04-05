from config import DEFAULT_MODEL
import re
import ollama

def get_completion_models(sort_by_param_count: bool = False) -> list[str]:
    """Список локальных моделей Ollama с capability completion.

    По умолчанию сортировка по имени. При ``sort_by_param_count=True`` —
    по числу параметров из суффикса ``:NNb`` (например ``gemma4:26b`` → 26).
    """
    result = []
    for m in ollama.list().models:
        if "completion" in ollama.show(m.model).capabilities:
            result.append(m.model)

    if not sort_by_param_count:
        return sorted(result)

    param_re = re.compile(r":(\d+)b")
    return sorted(
        result,
        key=lambda name: (int(param_re.search(name).group(1)), name),
    )

def get_least_params_model() -> str:
    """Модель с наименьшим числом параметров по суффиксу ``:NNb``; иначе резерв ``MODEL``."""
    models = get_completion_models(sort_by_param_count=True)
    return models[0] if models else DEFAULT_MODEL

def is_valid_completion_model(name: str) -> bool:
    return name in get_completion_models()


def format_completion_models_list(models: list[str] | None = None) -> str:
    if models is None:
        models = get_completion_models()
    if not models:
        return "Нет доступных моделей с capability completion."
    return "Доступные модели:\n" + "\n".join(f"• {m}" for m in models)
