# Local Development

OpenShorts is now focused on long-form video clipping and clip publishing. Docker is optional; the lightweight local path runs each service directly on Windows.

## Prerequisites

- Python 3.11 recommended
- Node.js 22+ and npm
- FFmpeg and ffprobe on PATH
- AI provider API key

## Run Services

Inside Codex, use the top-right Run button. It runs:

```powershell
.\scripts\start-codex-dev.ps1
```

That starts backend + dashboard, loads the Azure OpenAI key from the local Azure CLI session without saving the raw key in the repo, and writes logs to `%TEMP%\openshorts-codex`.

The Run action is safe to click repeatedly. If backend/dashboard are already listening, it reports them as already running instead of restarting them. To force a clean restart manually:

```powershell
.\scripts\start-codex-dev.ps1 -Restart
```

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

If backend env vars include `AI_API_KEY`, the dashboard can use that server-side key without storing the raw key in browser localStorage. The non-secret defaults are exposed at `/api/ai/defaults`.

The model selector reads non-secret model metadata from `/api/ai/models`. For Azure OpenAI it shows deployed, chat-capable deployments only; catalog models without deployment are not callable.

## Publishing

Upload-Post remains optional and downstream. Configure it in dashboard settings only when publishing clips.
