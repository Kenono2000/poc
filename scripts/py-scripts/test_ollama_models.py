import importlib.util
import os
import unittest
from pathlib import Path

SCRIPT_PATH = Path(__file__).with_name("ollama-models.py")
SPEC = importlib.util.spec_from_file_location("ollama_models", SCRIPT_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class OllamaModelsTests(unittest.TestCase):
    def test_get_timeout_seconds_uses_default_when_env_missing(self):
        os.environ.pop("OLLAMA_TIMEOUT_SECONDS", None)
        self.assertEqual(MODULE.get_timeout_seconds(), 60)

    def test_get_timeout_seconds_uses_env_override(self):
        os.environ["OLLAMA_TIMEOUT_SECONDS"] = "45"
        self.assertEqual(MODULE.get_timeout_seconds(), 45)

    def test_get_retry_attempts_uses_default_when_env_missing(self):
        os.environ.pop("OLLAMA_RETRY_ATTEMPTS", None)
        self.assertEqual(MODULE.get_retry_attempts(), 1)

    def test_get_retry_attempts_uses_env_override(self):
        os.environ["OLLAMA_RETRY_ATTEMPTS"] = "3"
        self.assertEqual(MODULE.get_retry_attempts(), 3)

    def test_get_ollama_host_prefers_cli_override(self):
        self.assertEqual(MODULE.get_ollama_host("https://cloud.example"), "https://cloud.example")

    def test_parse_cloud_page_models_extracts_library_names(self):
        html = '<a href="/library/gemma4">Gemma 4</a><a href="https://ollama.com/library/qwen3.5">Qwen 3.5</a><a href="/library/gemma4">Gemma 4 duplicate</a>'
        self.assertEqual(MODULE.parse_cloud_page_models(html), ["gemma4", "qwen3.5"])


if __name__ == "__main__":
    unittest.main()
