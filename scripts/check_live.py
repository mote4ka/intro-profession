"""Три реальных запроса из методички. Запуск: python scripts/check_live.py."""

from pathlib import Path
import sys

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from movie_api import MovieError, fetch_movie  # noqa: E402


def main() -> int:
    key = (dotenv_values(ROOT / ".env").get("OMDB_API_KEY") or "").strip()
    if not key:
        print("Заполните OMDB_API_KEY в .env перед проверкой.")
        return 1
    try:
        movie = fetch_movie("Batman", key)
    except MovieError as error:
        print(f"Существующий фильм: ошибка — {error}")
        return 1
    if movie.get("Title") != "Batman":
        print("Существующий фильм: получена неожиданная запись.")
        return 1
    print("Существующий фильм: OK")
    for label, title, test_key, expected in (
        ("Несуществующий фильм", "zzzz_uni_lab_no_such_movie_7b861cfe", key, "Фильм не найден"),
        ("Неверный ключ", "Batman", "invalid-lab-key", "Ошибка доступа"),
    ):
        try:
            fetch_movie(title, test_key)
        except MovieError as error:
            if expected not in str(error):
                print(f"{label}: ошибка — {error}")
                return 1
            print(f"{label}: OK — {error}")
        else:
            print(f"{label}: ожидалась ошибка, но получен результат.")
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
