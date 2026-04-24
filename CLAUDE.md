# Agent Context

This fork is being refocused into a long-form video clipping platform.

## Product Scope

Keep:

- Clip Generator
- AI transcript-to-clips analysis
- vertical crop/render pipeline
- subtitles and hook overlays
- clip download
- Upload-Post publishing

Do not reintroduce without explicit approval:

- AI Shorts / UGC actor generation
- fal.ai flows
- ElevenLabs dubbing
- thumbnail studio
- S3-first public gallery

## Runtime

Preferred local path is native Windows, not Docker:

- backend: `.\scripts\start-backend.ps1`
- dashboard: `.\scripts\start-dashboard.ps1`
- renderer: `.\scripts\start-renderer.ps1`

Docker remains optional and should not be assumed as the primary workflow on this machine.

## AI Providers

Clip selection is provider-agnostic through `ai_providers.py`.

Supported provider names:

- `gemini`
- `openai`
- `azure-openai`
- `openrouter`
- `nvidia-nim`
- `custom-openai-compatible`

Legacy Gemini headers/env are retained for compatibility.

## Azure

Azure CLI is available locally. Use `AZURE.md` and `PROJECT_REGISTRY.md` before touching cloud resources. Avoid creating paid compute unless the user has approved the specific cost/risk.
