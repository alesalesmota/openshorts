# OpenShorts Focused Clip Platform

OpenShorts turns long videos or YouTube URLs into short-form clips for TikTok, Instagram Reels, and YouTube Shorts.

This fork is focused on:

- AI-assisted long-form video clipping
- 9:16 vertical cropping
- subtitles and hook overlays
- clip download
- optional Upload-Post publishing
- model-provider agnostic clip analysis

Removed from this focused build:

- AI Shorts / UGC actor generation
- fal.ai actor/video generation
- ElevenLabs dubbing
- YouTube thumbnail studio
- S3-first public gallery surfaces

## Local Run

See [LOCAL_DEV.md](LOCAL_DEV.md).

Quick start from repo root:

```powershell
.\start.bat
```

Or run services manually:

```powershell
.\scripts\start-backend.ps1
```

```powershell
.\scripts\start-dashboard.ps1
```

Open:

```text
http://localhost:5175
```

Run renderer only when Remotion render workflows are needed:

```powershell
.\scripts\start-renderer.ps1
```

## AI Providers

The clip analysis layer supports:

- Gemini
- OpenAI
- Azure OpenAI
- OpenRouter
- NVIDIA NIM
- custom OpenAI-compatible endpoints

Primary request headers:

- `X-AI-Provider`
- `X-AI-Model`
- `X-AI-API-Key`
- `X-AI-Base-URL`
- `X-Azure-OpenAI-Endpoint`
- `X-Azure-OpenAI-Deployment`
- `X-Azure-OpenAI-API-Version`

Legacy `X-Gemini-Key` remains supported.

## Publishing

Upload-Post is optional and only used after clips are generated. Configure its key in dashboard settings to publish to TikTok, Instagram Reels, and YouTube Shorts.

## Azure

See [AZURE.md](AZURE.md). Azure is intended for heavy processing workers when local runs are too slow or resource-heavy.
