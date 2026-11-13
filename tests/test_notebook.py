"""Проверка всей последовательности ячеек, включая загрузку ключа."""

import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]
TEST_KEY = "notebook-test-secret"


class NotebookTests(unittest.TestCase):
    def run_notebook(self, env_file, title, data=None):
        notebook = json.loads((ROOT / "rest_api_demo.ipynb").read_text())
        output = io.StringIO()
        response = Mock()
        response.json.return_value = data
        with tempfile.TemporaryDirectory() as directory:
            Path(directory, ".env").write_text(env_file)
            with patch.dict(os.environ, {}, clear=True), patch("pathlib.Path.cwd", return_value=Path(directory)), patch("builtins.input", return_value=title), patch("movie_api.requests.get", return_value=response) as request, contextlib.redirect_stdout(output):
                namespace = {}
                for index, cell in enumerate(notebook["cells"]):
                    if cell["cell_type"] == "code":
                        source = "".join(cell["source"])
                        exec(compile(source, f"notebook-cell-{index}", "exec"), namespace)
                called = request.called
        self.assertNotIn(TEST_KEY, output.getvalue())
        return output.getvalue(), called

    def test_key_loaded_from_dotenv(self):
        output, called = self.run_notebook(
            f"OMDB_API_KEY={TEST_KEY}\n", "Batman",
            {"Response": "True", "Title": "Batman", "Year": "1989"},
        )
        self.assertTrue(called)
        self.assertIn('"Title": "Batman"', output)
        self.assertIn("Название: Batman", output)

    def test_missing_key_stops_before_network(self):
        output, called = self.run_notebook("", "Batman")
        self.assertFalse(called)
        self.assertIn("Заполните .env", output)

    def test_not_found_is_readable_without_empty_movie_fields(self):
        output, called = self.run_notebook(
            f"OMDB_API_KEY={TEST_KEY}\n", "NoSuchMovie",
            {"Response": "False", "Error": "Movie not found!"},
        )
        self.assertTrue(called)
        self.assertIn("Фильм не найден", output)
        self.assertNotIn("Название:", output)

    def test_invalid_key_is_readable(self):
        output, _ = self.run_notebook(
            f"OMDB_API_KEY={TEST_KEY}\n", "Batman",
            {"Response": "False", "Error": "Invalid API key!"},
        )
        self.assertIn("Ошибка доступа", output)
        self.assertNotIn("Название:", output)


if __name__ == "__main__":
    unittest.main()
