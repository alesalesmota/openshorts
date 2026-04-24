# Local Development

OpenShorts is now focused on long-form video clipping and clip publishing. Docker is optional; the lightweight local path runs each service directly on Windows.

## Prerequisites

- Python 3.11 recommended
- Node.js 22+ and npm
- FFmpeg and ffprobe on PATH
- AI provider API key

## Run Services

Open three PowerShell windows from the repository root:

```powershell
.\scripts\start-backend.ps1
```

If Python dependencies are missing:

```powershell
.\scripts\start-backend.ps1 -Install
```

Use an isolated virtualenv only when you want dependency isolation and accept extra disk use:

```powershell
.\scripts\start-backend.ps1 -UseVenv -Install
```

```powershell
.\scripts\start-dashboard.ps1
```

```powershell
.\scripts\start-renderer.ps1
```

Default URLs:

- Dashboard: `http://localhost:5175`
- Backend API: `http://localhost:8000`
- Renderer: `http://localhost:3100`

The renderer is only needed for browser/Remotion render workflows. Basic clip generation uses backend + dashboard.

## AI Providers

The dashboard sends provider settings per request. Backend env vars are fallback defaults:

- `AI_PROVIDER`: `gemini`, `openai`, `azure-openai`, `openrouter`, `nvidia-nim`, or `custom-openai-compatible`
- `AI_MODEL`
- `AI_API_KEY`
- `AI_BASE_URL` for OpenAI-compatible providers when needed
- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_DEPLOYMENT`, `AZURE_OPENAI_API_VERSION` for Azure OpenAI

Legacy `X-Gemini-Key` and `GEMINI_API_KEY` still work for Gemini.

## Publishing

Upload-Post remains optional and downstream. Configure it in dashboard settings only when publishing clips.
