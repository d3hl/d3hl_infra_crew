import os
import unittest
from unittest.mock import patch

from d3hl_infra_crew.crews.infrastructure_crew.infrastructure_crew import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_OPENROUTER_MODEL,
    configured_llm,
)


class LlmConfigTests(unittest.TestCase):
    def test_uses_openrouter_default_when_only_openrouter_key_is_present(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}, clear=True):
            llm = configured_llm()
        self.assertIsNotNone(llm)
        self.assertEqual(llm.model, "deepseek/deepseek-v4-pro")
        self.assertEqual(llm.provider, "openrouter")
        self.assertEqual(llm.max_tokens, DEFAULT_MAX_TOKENS)

    def test_explicit_model_env_wins(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "MODEL": "openrouter/meta-llama/llama-3.1-8b-instruct",
            },
            clear=True,
        ):
            llm = configured_llm()
        self.assertIsNotNone(llm)
        self.assertEqual(llm.provider, "openrouter")
        self.assertEqual(llm.model, "meta-llama/llama-3.1-8b-instruct")

    def test_token_cap_env_wins(self):
        with patch.dict(
            os.environ,
            {
                "OPENROUTER_API_KEY": "test-key",
                "CREWAI_MAX_TOKENS": "2048",
            },
            clear=True,
        ):
            llm = configured_llm()
        self.assertIsNotNone(llm)
        self.assertEqual(llm.max_tokens, 2048)

    def test_returns_none_without_model_or_provider_key(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsNone(configured_llm())

    def test_default_model_keeps_provider_prefix(self):
        self.assertTrue(DEFAULT_OPENROUTER_MODEL.startswith("openrouter/"))


if __name__ == "__main__":
    unittest.main()
