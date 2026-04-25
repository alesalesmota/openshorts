import unittest
from unittest.mock import patch

from ai_providers import AIProviderConfig, ClipAnalysisError, analyze_clips, parse_clip_json


TRANSCRIPT = {
    "text": "This is a useful workflow. Follow for more.",
    "segments": [
        {
            "text": "This is a useful workflow.",
            "start": 0,
            "end": 3,
            "words": [
                {"word": "This", "start": 0.0, "end": 0.2},
                {"word": "workflow", "start": 1.0, "end": 1.4},
            ],
        }
    ],
}

CLIP_JSON = {
    "shorts": [
        {
            "start": 0,
            "end": 15,
            "video_description_for_tiktok": "Watch this workflow. Follow for more.",
            "video_description_for_instagram": "Watch this workflow. Follow for more.",
            "video_title_for_youtube_short": "Useful Workflow",
            "viral_hook_text": "Steal this workflow",
        }
    ]
}


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        self.requests.append((args, kwargs))
        return FakeResponse({
            "choices": [{"message": {"content": '{"shorts":[{"start":0,"end":15,"video_description_for_tiktok":"TikTok","video_title_for_youtube_short":"Title","viral_hook_text":"Hook"}]}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        })


class AIProvidersTest(unittest.TestCase):
    def test_parse_clip_json_strips_markdown(self):
        result = parse_clip_json(f"```json\n{CLIP_JSON!r}\n```".replace("'", '"'))
        self.assertEqual(result["shorts"][0]["start"], 0)
        self.assertEqual(result["shorts"][0]["end"], 15)

    def test_missing_key_fails_cleanly(self):
        config = AIProviderConfig(provider="openai", api_key="", model="gpt-4o-mini")
        with self.assertRaises(ClipAnalysisError):
            analyze_clips(TRANSCRIPT, 30, config)

    def test_gemini_adapter_can_be_mocked(self):
        config = AIProviderConfig(provider="gemini", api_key="key", model="gemini-2.5-flash")
        with patch("ai_providers._call_gemini", return_value=('{"shorts":[{"start":0,"end":15,"video_description_for_tiktok":"TikTok","video_title_for_youtube_short":"Title","viral_hook_text":"Hook"}]}', {"total_tokens": 15})):
            result = analyze_clips(TRANSCRIPT, 30, config)
        self.assertEqual(result["shorts"][0]["video_title_for_youtube_short"], "Title")
        self.assertEqual(result["cost_analysis"]["provider"], "gemini")

    def test_ai_clip_ranges_are_normalized(self):
        config = AIProviderConfig(provider="gemini", api_key="key", model="gemini-2.5-flash")
        payload = '{"shorts":[{"start":10,"end":500,"video_description_for_tiktok":"TikTok","video_title_for_youtube_short":"Title","viral_hook_text":"Hook"},{"start":80,"end":82,"video_description_for_tiktok":"Short","video_title_for_youtube_short":"Short","viral_hook_text":"Hook"}]}'
        with patch("ai_providers._call_gemini", return_value=(payload, {})):
            result = analyze_clips(TRANSCRIPT, 100, config)

        self.assertEqual(result["shorts"][0]["start"], 10)
        self.assertEqual(result["shorts"][0]["end"], 70)
        self.assertEqual(result["shorts"][1]["start"], 80)
        self.assertEqual(result["shorts"][1]["end"], 95)

    @patch("httpx.Client", FakeClient)
    def test_openai_compatible_adapter(self):
        config = AIProviderConfig(provider="openai", api_key="key", model="gpt-4o-mini")
        result = analyze_clips(TRANSCRIPT, 30, config)
        self.assertEqual(result["cost_analysis"]["provider"], "openai")
        self.assertEqual(result["cost_analysis"]["usage"]["prompt_tokens"], 10)

    @patch("httpx.Client", FakeClient)
    def test_azure_openai_adapter(self):
        config = AIProviderConfig(
            provider="azure-openai",
            api_key="key",
            model="deployment",
            azure_endpoint="https://example.openai.azure.com",
            azure_deployment="deployment",
        )
        result = analyze_clips(TRANSCRIPT, 30, config)
        self.assertEqual(result["cost_analysis"]["provider"], "azure-openai")


if __name__ == "__main__":
    unittest.main()
