import os
import unittest
from unittest.mock import patch

from app import build_ai_env


class RequestStub:
    def __init__(self, headers):
        self.headers = headers


class AppHeaderMappingTest(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_legacy_gemini_key_maps_to_ai_env(self):
        env = build_ai_env(RequestStub({"X-Gemini-Key": "legacy-key"}))

        self.assertEqual(env["AI_PROVIDER"], "gemini")
        self.assertEqual(env["AI_API_KEY"], "legacy-key")
        self.assertEqual(env["GEMINI_API_KEY"], "legacy-key")

    @patch.dict(os.environ, {}, clear=True)
    def test_ai_headers_map_to_env(self):
        env = build_ai_env(
            RequestStub({
                "X-AI-Provider": "openai",
                "X-AI-Model": "gpt-4o-mini",
                "X-AI-API-Key": "provider-key",
                "X-AI-Base-URL": "https://api.openai.com/v1",
            })
        )

        self.assertEqual(env["AI_PROVIDER"], "openai")
        self.assertEqual(env["AI_MODEL"], "gpt-4o-mini")
        self.assertEqual(env["AI_API_KEY"], "provider-key")
        self.assertEqual(env["AI_BASE_URL"], "https://api.openai.com/v1")


if __name__ == "__main__":
    unittest.main()
