# OpenShorts Focused Clip Platform Implementation Plan

## Goal

Refocus this fork into a long-form video clipping/editing app with local lightweight development, optional Azure heavy-processing path, Upload-Post publishing, and provider-agnostic transcript-to-clips AI analysis.

## Scope

- Keep Clip Generator, clip review/editing, download, and Upload-Post publishing.
- Remove non-core product flows: AI Shorts/UGC actor generation, fal.ai generation, ElevenLabs dubbing, thumbnail studio, and S3-first gallery surfaces.
- Keep Docker optional; native Windows scripts are the primary local path.
- Add AI provider contract for Gemini, OpenAI, Azure OpenAI, OpenRouter, NVIDIA NIM, and custom OpenAI-compatible endpoints.
- Preserve legacy `X-Gemini-Key` compatibility.

## Implementation Notes

- Product prune lives in dedicated commit `6d47ec8 refactor: focus app on clip workflow`.
- AI clip analysis lives in `ai_providers.py`.
- `main.py` delegates prompt construction, provider calls, JSON parsing, and validation to the provider layer.
- `app.py` maps provider headers into subprocess environment variables for `/api/process`.
- Dashboard Settings now owns AI provider config and Upload-Post config separately.
- Azure docs/scripts are preparatory only; no Azure resources should be created without explicit cost-aware approval.

## Follow-Up Candidates

- Move Gemini video-upload editing/effects into a second provider abstraction if non-Gemini multimodal editing becomes required.
- Add real end-to-end provider tests using small videos and low-cost models once user keys are available.
- Add Azure worker deployment after quota and cost defaults are confirmed.
