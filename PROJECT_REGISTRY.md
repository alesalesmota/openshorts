# Project Registry

## Current State

- Repository cloned locally at `C:\Users\Blue_\Desktop\PROJETOS\openshorts`.
- Fork created at `https://github.com/alesalesmota/openshorts`.
- Git remotes:
  - `origin`: `https://github.com/alesalesmota/openshorts.git`
  - `upstream`: `https://github.com/mutonby/openshorts.git`

## Local Verification

- Dashboard dependencies installed with `npm ci`; production build passes.
- Render service dependencies installed with `npm ci`; TypeScript build passes.
- Python syntax compile check passes for main backend modules.
- Python unit tests pass with provider adapter mocks and header compatibility tests.
- Runtime imports for OpenShorts dependencies pass on system Python after installing missing user-level packages.
- Dashboard dev server is running on `http://localhost:5175`.
- Backend dev server is running on `http://localhost:8000`.
- Renderer is not running by default; start `scripts\start-renderer.ps1` only for Remotion render workflows.
- `pip check` still reports unrelated global Python conflicts from other installed projects (`tts`, `pyannote`, `montreal-forced-aligner`, `trainer`). OpenShorts runtime imports currently pass.
- Docker is optional for this fork and is not required for the lightweight local path.

## Runtime Notes

- Primary lightweight run path is native Windows, no Docker required.
- Dashboard URL: `http://localhost:5175`.
- Backend API URL: `http://localhost:8000`.
- Renderer URL: `http://localhost:3100`, only needed for Remotion/browser render workflows.
- Clip analysis requires one AI provider key. Supported providers are Gemini, OpenAI, Azure OpenAI, OpenRouter, NVIDIA NIM, and custom OpenAI-compatible endpoints.
- Upload-Post is optional and separate from AI provider config.

## Product Direction Notes

- Current intended direction is long-form video cutting and editing workflows only.
- Priority feature area: Clip Generator / long video to short clips.
- AI Shorts with generated actors was removed from this focused fork.
- ElevenLabs, fal.ai, thumbnail studio, and S3-first gallery surfaces were removed from this focused fork.
- Upload-Post remains in scope for publishing finished clips to TikTok, Instagram Reels, and YouTube Shorts.
- Azure Blob may be added later as optional cloud storage for heavy processing, but local-first output remains preferred for lightweight use.

## Architecture Observations

- Clip Generator now uses `ai_providers.py` for transcript-to-clips analysis.
- `main.py` delegates prompt construction, provider calls, JSON parsing, and clip metadata validation to the provider layer.
- `app.py` maps request headers into provider environment variables for the clip subprocess.
- `X-Gemini-Key` still maps to Gemini for backward compatibility.
- Keep Upload-Post integration separate from AI provider work; publishing is a downstream workflow and should not affect clip detection.
- Auto Edit/effects still require Gemini because that path uses Gemini video upload; only transcript-to-clips analysis is provider-agnostic in this implementation.

## Lightweight Local Run Notes

- Rancher Desktop was installed as a Docker-compatible option, but WSL/Rancher consumed about 7.9 GB RAM during setup/build.
- Rancher/WSL is currently stopped.
- Preferred exploration path for this computer is native local run without Docker:
  - dashboard via Vite on `http://localhost:5175`
  - backend via Python/FastAPI on `http://localhost:8000`
  - renderer via Node on `http://localhost:3100` only when needed
- FFmpeg and ffprobe are installed globally through Scoop.
- Missing OpenShorts runtime packages installed at user level for current system Python: `scenedetect`, `ultralytics`, `mediapipe`, `google-genai`, compatible `torchvision`, and related dependencies.
- Local scripts:
  - `scripts\start-backend.ps1`
  - `scripts\start-dashboard.ps1`
  - `scripts\start-renderer.ps1`
  - `scripts\start-codex-dev.ps1`
- Codex top-right Run action starts `scripts\start-codex-dev.ps1` from the repo root. It launches backend + dashboard, fetches the Azure OpenAI key through local Azure CLI only for the backend process environment, and writes runtime logs to `%TEMP%\openshorts-codex`.
- The Codex Run script is idempotent: repeated clicks report existing backend/dashboard instead of restarting them. Use `scripts\start-codex-dev.ps1 -Restart` only when a clean restart is needed.
- Root `start.bat` is a user-facing launcher for the same backend + dashboard startup path. It can be run from repo root or double-clicked, and forwards arguments such as `-Restart` to `scripts\start-codex-dev.ps1`.

## Azure Access Notes

- Azure CLI is installed locally through `winget` (`Microsoft.AzureCLI`).
- CLI path for current Windows install: `C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd`.
- Preferred auth method is interactive local login with `az login`; do not store raw Azure secrets in the repo.
- Current Azure CLI login is valid.
- Default subscription:
  - name: `Azure subscription 1`
  - subscription id: `cd1eff50-8be3-4eea-beb8-c7bc4e521df8`
  - tenant id: `01f7a33b-8dff-4684-a60d-d2eaed42aa79`
  - account: `Blue_008_36@hotmail.com`
- Future agents should use the local Azure CLI session when available:
  - check login: `az account show`
  - list subscriptions: `az account list --output table`
  - set subscription: `az account set --subscription <subscription-id-or-name>`
- Scope guideline: prefer creating/using a dedicated resource group such as `rg-openshorts` rather than operating broadly across the subscription.
- Cost guideline: prefer low-cost resources by default and stop/delete compute when not actively testing video jobs.
- Non-mutating Azure CLI account check passes.
- `az vm list-usage --location eastus` returned an empty list in this subscription at the time of implementation; no Azure resources were created.
- Existing Azure AI Services resource found:
  - name: `blue-008-36-2109-resource`
  - resource group: `rg-Blue_008_36-2109`
  - region: `eastus2`
  - endpoint: `https://blue-008-36-2109-resource.cognitiveservices.azure.com/`
  - sku: `S0`
- Azure OpenAI deployment created for local OpenShorts testing:
  - deployment: `openshorts-gpt-4-1-mini`
  - model: `gpt-4.1-mini`
  - model version: `2025-04-14`
  - sku: `Standard`
  - capacity: `1`
- Backend now supports non-secret AI defaults at `/api/ai/defaults`, allowing local sessions to use a server-side API key without storing the raw key in browser localStorage.
- Backend now supports non-secret model/deployment discovery at `/api/ai/models`.
- Azure model discovery returns only deployed, chat-capable, succeeded deployments. Catalog-only Azure models are intentionally hidden because they are not callable until deployed.
- Dashboard Settings uses a model/deployment dropdown with status metadata and sort modes: recommended, cheapest, smartest, newest, fastest.
- Current local backend session was started with Azure OpenAI env vars and `has_api_key=true`; temp key file was deleted after process start.
- A minimal Azure chat completions ping returned `{"ok":true}`.
- Candidate models available in that resource include `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5.4-mini`, and newer listed models as of the local CLI check on 2026-04-24.
- Do not store Azure API keys in repo files. Retrieve keys via CLI only when configuring local runtime, Key Vault, or explicit user-approved deployment flow.
- Local backend worker startup is sensitive to Windows stdio encoding when launched headless. `app.py` now reconfigures stdout/stderr as UTF-8 and logs crashed background tasks so queue failures are visible.
- Local Python runtime for the clip pipeline is pinned to `mediapipe==0.10.14`, `numpy==1.26.4`, and OpenCV `4.11.0.86` because `mediapipe==0.10.33` no longer exposes the `mp.solutions` API used by `main.py`.
- On Windows local CPU runs, MediaPipe/TFLite and Faster-Whisper can both load Intel OpenMP and crash with `OMP: Error #15: Initializing libiomp5md.dll`. Job subprocesses set `KMP_DUPLICATE_LIB_OK=TRUE` and `OMP_NUM_THREADS=1` to keep local transcription usable.
- Azure clip analysis may return ranges outside the renderer contract. `ai_providers.py` now normalizes AI clip ranges into the supported 15-60 second window instead of failing the whole job for fixable model output.
- `main.py` no longer renders the full source video as a fallback when clip analysis fails. Jobs now fail early with a clear log instead of producing an unusable whole-video short without metadata.
- End-to-end local validation on 2026-04-24 used a generated 60s spoken fixture through backend upload, Faster-Whisper, Azure OpenAI deployment `openshorts-gpt-4-1-mini`, metadata generation, and local rendering. Job `1e87e327-e995-4df4-a4f7-cb886df0c61a` completed with 5 rendered clips and metadata.
