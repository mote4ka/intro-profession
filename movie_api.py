"""Запрос к OMDb и форматирование результата без вывода секретов."""

from typing import Any

import requests


OMDB_URL = "https://www.omdbapi.com/"
REQUEST_TIMEOUT = 15


class MovieError(Exception):
    """Понятная пользователю ошибка поиска фильма."""


def fetch_movie(title: str, api_key: str) -> dict[str, Any]:
    """Получить одну запись по названию; HTTP 200 ещё не означает успех OMDb."""
    title = title.strip()
    api_key = api_key.strip()
    if not title:
        raise MovieError("Введите непустое название фильма.")
    if not api_key:
        raise MovieError("Ключ OMDB_API_KEY не найден. Заполните .env.")

    try:
        response = requests.get(
            OMDB_URL,
            params={"t": title, "apikey": api_key},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
    except requests.Timeout:
        raise MovieError("Сервис не ответил вовремя. Повторите запрос позже.") from None
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else None
        if status in (401, 403):
            message = "Ошибка доступа: проверьте API-ключ и его активацию."
        elif status == 429:
            message = "Превышен лимит запросов OMDb. Повторите позже."
        else:
            message = "Ошибка HTTP при обращении к OMDb. Повторите позже."
        # str(error) может содержать URL с apikey: не выводим исходное исключение.
        raise MovieError(message) from None
    except requests.RequestException:
        raise MovieError("Не удалось подключиться к OMDb. Проверьте соединение.") from None

    try:
        data = response.json()
    except ValueError:
        raise MovieError("OMDb вернул некорректный JSON.") from None

    if not isinstance(data, dict):
        raise MovieError("Неожиданный формат ответа OMDb: ожидался JSON-объект.")

    if data.get("Response") == "False":
        reason = str(data.get("Error", "")).lower()
        if "not found" in reason:
            message = "Фильм не найден. Проверьте название (лучше на английском)."
        elif "api key" in reason or "apikey" in reason:
            message = "Ошибка доступа: проверьте API-ключ и его активацию."
        elif "limit" in reason:
            message = "Превышен лимит запросов OMDb. Повторите позже."
        else:
            # Не отражаем произвольное тело ошибки сервиса в выводе ноутбука.
            message = "OMDb не смог выполнить поиск. Проверьте параметры запроса."
        raise MovieError(message)

    if (
        data.get("Response") != "True"
        or not isinstance(data.get("Title"), str)
        or not data["Title"].strip()
    ):
        raise MovieError("Неожиданный формат ответа OMDb: отсутствуют данные фильма.")
    return data


def format_movie(movie: dict[str, Any]) -> str:
    """Сформировать основные поля, актёров и краткую итоговую строку."""
    fields = (
        ("Title", "Название"),
        ("Year", "Год"),
        ("Genre", "Жанр"),
        ("Director", "Режиссёр"),
        ("imdbRating", "Рейтинг IMDb"),
        ("Actors", "Актёры"),
    )
    values = {}
    for field, _ in fields:
        value = movie.get(field)
        values[field] = "Нет данных" if value in (None, "", "N/A") else str(value)
    lines = [f"{label}: {values[field]}" for field, label in fields]
    lines.append(
        f"\nФильм «{values['Title']}» ({values['Year']}) — жанр: {values['Genre']}. "
        f"Режиссёр: {values['Director']}."
    )
    return "\n".join(lines)
