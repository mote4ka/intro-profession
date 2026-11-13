"""Изолированные проверки: реальные ключи и сеть не используются."""

import unittest
from unittest.mock import Mock, patch

import requests

from movie_api import MovieError, fetch_movie, format_movie


MOVIE = {
    "Response": "True", "Title": "Batman", "Year": "1989",
    "Genre": "Action, Adventure", "Director": "Tim Burton",
    "Actors": "Michael Keaton, Jack Nicholson", "imdbRating": "7.5",
}
TEST_KEY = "local-test-secret"


class MovieApiTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("movie_api.requests.get")
        self.get = patcher.start()
        self.addCleanup(patcher.stop)
        self.response = self.get.return_value
        self.response.json.return_value = MOVIE.copy()

    def test_existing_movie_and_safe_transport(self):
        movie = fetch_movie("  Batman  ", TEST_KEY)
        self.assertEqual(movie["Year"], "1989")
        self.get.assert_called_once_with(
            "https://www.omdbapi.com/",
            params={"t": "Batman", "apikey": TEST_KEY}, timeout=15,
        )
        self.response.raise_for_status.assert_called_once()
        output = format_movie(movie)
        for value in ("Название: Batman", "Год: 1989", "Режиссёр: Tim Burton", "Актёры: Michael Keaton", "Рейтинг IMDb: 7.5"):
            self.assertIn(value, output)
        self.assertNotIn(TEST_KEY, output)

    def test_empty_input_does_not_send_request(self):
        for title, key, message in (("  ", TEST_KEY, "название"), ("Batman", "  ", "OMDB_API_KEY")):
            with self.subTest(title=title):
                with self.assertRaisesRegex(MovieError, message):
                    fetch_movie(title, key)
        self.get.assert_not_called()

    def test_service_error_even_on_http_success(self):
        for error, message in (
            ("Movie not found!", "Фильм не найден"),
            ("Invalid API key!", "Ошибка доступа"),
            ("No API key provided.", "Ошибка доступа"),
            ("Request limit reached!", "лимит"),
            ("Unexpected error " + TEST_KEY, "не смог выполнить поиск"),
        ):
            with self.subTest(error=error):
                self.response.json.return_value = {"Response": "False", "Error": error}
                with self.assertRaisesRegex(MovieError, message) as result:
                    fetch_movie("Batman", TEST_KEY)
                self.assertNotIn(TEST_KEY, str(result.exception))

    def test_http_errors_do_not_disclose_url_or_key(self):
        for status, message in ((401, "Ошибка доступа"), (403, "Ошибка доступа"), (429, "лимит"), (500, "Ошибка HTTP")):
            with self.subTest(status=status):
                response = requests.Response()
                response.status_code = status
                self.response.raise_for_status.side_effect = requests.HTTPError(
                    "https://www.omdbapi.com/?apikey=" + TEST_KEY, response=response,
                )
                with self.assertRaisesRegex(MovieError, message) as result:
                    fetch_movie("Batman", TEST_KEY)
                self.assertNotIn(TEST_KEY, str(result.exception))
                self.assertNotIn("apikey=", str(result.exception))
        self.response.json.assert_not_called()

    def test_network_errors_do_not_disclose_key(self):
        for error, message in ((requests.Timeout(TEST_KEY), "не ответил вовремя"), (requests.ConnectionError(TEST_KEY), "соединение")):
            with self.subTest(kind=type(error).__name__):
                self.get.side_effect = error
                with self.assertRaisesRegex(MovieError, message) as result:
                    fetch_movie("Batman", TEST_KEY)
                self.assertNotIn(TEST_KEY, str(result.exception))

    def test_broken_json(self):
        self.response.json.side_effect = ValueError(TEST_KEY)
        with self.assertRaisesRegex(MovieError, "некорректный JSON"):
            fetch_movie("Batman", TEST_KEY)

    def test_unexpected_payload(self):
        for payload in ([], None, "text", {}, {"Response": "True"}, {"Response": True, "Title": "Batman"}):
            with self.subTest(payload=payload):
                self.response.json.return_value = payload
                with self.assertRaisesRegex(MovieError, "формат ответа"):
                    fetch_movie("Batman", TEST_KEY)

    def test_missing_optional_fields(self):
        text = format_movie({"Title": "Batman", "Actors": "N/A", "Year": None})
        self.assertIn("Название: Batman", text)
        self.assertIn("Актёры: Нет данных", text)
        self.assertIn("Год: Нет данных", text)


if __name__ == "__main__":
    unittest.main()
