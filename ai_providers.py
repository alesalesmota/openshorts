import json
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx


class ClipAnalysisError(Exception):
    """Raised when an AI provider cannot produce valid clip metadata."""


@dataclass
class AIProviderConfig:
    provider: str
    api_key: str
    model: str
    base_url: Optional[str] = None
    azure_endpoint: Optional[str] = None
    azure_deployment: Optional[str] = None
    azure_api_version: str = "2024-10-21"


CLIP_ANALYSIS_PROMPT_TEMPLATE = """
You are a senior short-form video editor. Read the ENTIRE transcript and word-level timestamps to choose the 3-15 MOST VIRAL moments for TikTok/IG Reels/YouTube Shorts. Each clip must be between 15 and 60 seconds long.

FFMPEG TIME CONTRACT - STRICT REQUIREMENTS:
- Return timestamps in ABSOLUTE SECONDS from the start of the video (usable in: ffmpeg -ss <start> -to <end> -i <input> ...).
- Only NUMBERS with decimal point, up to 3 decimals (examples: 0, 1.250, 17.350).
- Ensure 0 <= start < end <= VIDEO_DURATION_SECONDS.
- Each clip between 15 and 60 s (inclusive).
- Prefer starting 0.2-0.4 s BEFORE the hook and ending 0.2-0.4 s AFTER the payoff.
- Use silence moments for natural cuts; never cut in the middle of a word or phrase.
- STRICTLY FORBIDDEN to use time formats other than absolute seconds.

VIDEO_DURATION_SECONDS: {video_duration}

TRANSCRIPT_TEXT (raw):
{transcript_text}

WORDS_JSON (array of {{w, s, e}} where s/e are seconds):
{words_json}

STRICT EXCLUSIONS:
- No generic intros/outros or purely sponsorship segments unless they contain the hook.
- No clips < 15 s or > 60 s.

OUTPUT - RETURN ONLY VALID JSON (no markdown, no comments). Order clips by predicted performance (best to worst). In the descriptions, ALWAYS include a CTA like "Follow me and comment X and I'll send you the workflow" when it fits the content:
{{
  "shorts": [
    {{
      "start": <number in seconds, e.g., 12.340>,
      "end": <number in seconds, e.g., 37.900>,
      "video_description_for_tiktok": "<description for TikTok oriented to get views>",
      "video_description_for_instagram": "<description for Instagram oriented to get views>",
      "video_title_for_youtube_short": "<title for YouTube Short oriented to get views 100 chars max>",
      "viral_hook_text": "<SHORT punchy text overlay (max 10 words). MUST BE IN THE SAME LANGUAGE AS THE VIDEO TRANSCRIPT.>"
    }}
  ]
}}
"""


def config_from_env() -> AIProviderConfig:
    legacy_gemini_key = os.getenv("GEMINI_API_KEY")
    provider = (os.getenv("AI_PROVIDER") or ("gemini" if legacy_gemini_key else "")).strip().lower()
    api_key = (os.getenv("AI_API_KEY") or legacy_gemini_key or "").strip()

    if not provider:
        provider = "gemini"

    model = (os.getenv("AI_MODEL") or "").strip()
    if not model:
        model = _default_model(provider)

    return AIProviderConfig(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=(os.getenv("AI_BASE_URL") or "").strip() or None,
        azure_endpoint=(os.getenv("AZURE_OPENAI_ENDPOINT") or "").strip() or None,
        azure_deployment=(os.getenv("AZURE_OPENAI_DEPLOYMENT") or "").strip() or None,
        azure_api_version=(os.getenv("AZURE_OPENAI_API_VERSION") or "2024-10-21").strip(),
    )


def analyze_clips(transcript_result: Dict[str, Any], video_duration: float, config: Optional[AIProviderConfig] = None) -> Dict[str, Any]:
    config = config or config_from_env()
    if not config.api_key:
        raise ClipAnalysisError("Missing AI API key. Set AI_API_KEY or pass X-AI-API-Key.")

    prompt = build_clip_analysis_prompt(transcript_result, video_duration)

    if config.provider == "gemini":
        text, usage = _call_gemini(config, prompt)
    elif config.provider == "azure-openai":
        text, usage = _call_azure_openai(config, prompt)
    elif config.provider in {"openai", "openrouter", "nvidia-nim", "custom-openai-compatible"}:
        text, usage = _call_openai_compatible(config, prompt)
    else:
        raise ClipAnalysisError(f"Unsupported AI provider: {config.provider}")

    parsed = parse_clip_json(text)
    _validate_clip_ranges(parsed, video_duration)
    parsed["cost_analysis"] = {
        "provider": config.provider,
        "model": config.model,
        "usage": usage,
    }
    return parsed


def build_clip_analysis_prompt(transcript_result: Dict[str, Any], video_duration: float) -> str:
    words: List[Dict[str, Any]] = []
    for segment in transcript_result.get("segments", []):
        for word in segment.get("words", []):
            words.append({
                "w": word.get("word", ""),
                "s": word.get("start"),
                "e": word.get("end"),
            })

    return CLIP_ANALYSIS_PROMPT_TEMPLATE.format(
        video_duration=round(float(video_duration), 3),
        transcript_text=json.dumps(transcript_result.get("text", ""), ensure_ascii=False),
        words_json=json.dumps(words, ensure_ascii=False),
    )


def parse_clip_json(raw_text: str) -> Dict[str, Any]:
    text = _extract_json_text(raw_text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ClipAnalysisError(f"AI provider returned invalid JSON: {exc}") from exc

    shorts = data.get("shorts")
    if not isinstance(shorts, list) or not shorts:
        raise ClipAnalysisError("AI provider returned no shorts.")

    normalized = []
    for index, clip in enumerate(shorts):
        if not isinstance(clip, dict):
            raise ClipAnalysisError(f"Clip {index + 1} is not an object.")
        try:
            start = float(clip["start"])
            end = float(clip["end"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ClipAnalysisError(f"Clip {index + 1} has invalid start/end values.") from exc
        if start < 0 or end <= start:
            raise ClipAnalysisError(f"Clip {index + 1} has invalid time range.")

        normalized.append({
            "start": round(start, 3),
            "end": round(end, 3),
            "video_description_for_tiktok": str(clip.get("video_description_for_tiktok") or ""),
            "video_description_for_instagram": str(clip.get("video_description_for_instagram") or clip.get("video_description_for_tiktok") or ""),
            "video_title_for_youtube_short": str(clip.get("video_title_for_youtube_short") or "Generated Short")[:100],
            "viral_hook_text": str(clip.get("viral_hook_text") or "Watch this"),
        })

    data["shorts"] = normalized
    return data


def _validate_clip_ranges(data: Dict[str, Any], video_duration: float) -> None:
    max_duration = float(video_duration)
    for index, clip in enumerate(data.get("shorts", [])):
        start = float(clip["start"])
        end = float(clip["end"])
        duration = end - start
        if end > max_duration:
            raise ClipAnalysisError(f"Clip {index + 1} ends after the source video duration.")
        if duration < 15 or duration > 60:
            raise ClipAnalysisError(f"Clip {index + 1} duration must be between 15 and 60 seconds.")


def _call_gemini(config: AIProviderConfig, prompt: str) -> tuple[str, Dict[str, Any]]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=config.api_key)
    response = client.models.generate_content(
        model=config.model,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    usage = {}
    usage_metadata = getattr(response, "usage_metadata", None)
    if usage_metadata:
        usage = {
            "prompt_tokens": getattr(usage_metadata, "prompt_token_count", None),
            "completion_tokens": getattr(usage_metadata, "candidates_token_count", None),
            "total_tokens": getattr(usage_metadata, "total_token_count", None),
        }
    return response.text or "", usage


def _call_openai_compatible(config: AIProviderConfig, prompt: str) -> tuple[str, Dict[str, Any]]:
    base_url = (config.base_url or _default_base_url(config.provider)).rstrip("/")
    if not base_url:
        raise ClipAnalysisError("OpenAI-compatible providers require AI_BASE_URL or X-AI-Base-URL.")
    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    if config.provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost:5175"
        headers["X-Title"] = "OpenShorts"

    payload = _chat_payload(config.model, prompt)
    with httpx.Client(timeout=120.0) as client:
        data = _post_chat(client, url, headers=headers, payload=payload)

    return _extract_chat_content(data), data.get("usage", {})


def _call_azure_openai(config: AIProviderConfig, prompt: str) -> tuple[str, Dict[str, Any]]:
    endpoint = (config.azure_endpoint or config.base_url or "").rstrip("/")
    deployment = config.azure_deployment or config.model
    if not endpoint:
        raise ClipAnalysisError("Azure OpenAI requires AZURE_OPENAI_ENDPOINT or X-Azure-OpenAI-Endpoint.")
    if not deployment:
        raise ClipAnalysisError("Azure OpenAI requires AZURE_OPENAI_DEPLOYMENT or X-AI-Model.")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions"
    params = {"api-version": config.azure_api_version}
    headers = {
        "api-key": config.api_key,
        "Content-Type": "application/json",
    }
    payload = _chat_payload(deployment, prompt)
    payload.pop("model", None)

    with httpx.Client(timeout=120.0) as client:
        data = _post_chat(client, url, params=params, headers=headers, payload=payload)

    return _extract_chat_content(data), data.get("usage", {})


def _post_chat(client: httpx.Client, url: str, headers: Dict[str, str], payload: Dict[str, Any], params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        response = client.post(url, params=params, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code not in {400, 422} or "response_format" not in payload:
            raise ClipAnalysisError(f"AI provider HTTP error: {exc.response.status_code} {exc.response.text}") from exc

    fallback_payload = dict(payload)
    fallback_payload.pop("response_format", None)
    try:
        response = client.post(url, params=params, headers=headers, json=fallback_payload)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        raise ClipAnalysisError(f"AI provider HTTP error: {exc.response.status_code} {exc.response.text}") from exc


def _chat_payload(model: str, prompt: str) -> Dict[str, Any]:
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You return strict JSON only. No markdown, comments, or prose outside JSON.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }


def _extract_chat_content(data: Dict[str, Any]) -> str:
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise ClipAnalysisError("AI provider returned an unexpected chat response shape.") from exc


def _extract_json_text(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE).strip()
        text = re.sub(r"```$", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _default_model(provider: str) -> str:
    return {
        "gemini": "gemini-2.5-flash",
        "openai": "gpt-4o-mini",
        "azure-openai": "",
        "openrouter": "openai/gpt-4o-mini",
        "nvidia-nim": "meta/llama-3.1-70b-instruct",
        "custom-openai-compatible": "",
    }.get(provider, "")


def _default_base_url(provider: str) -> str:
    return {
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "nvidia-nim": "https://integrate.api.nvidia.com/v1",
    }.get(provider, "")
