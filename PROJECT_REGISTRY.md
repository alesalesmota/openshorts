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
- No Azure OpenAI model deployments exist in that resource yet.
- Candidate models available in that resource include `gpt-4o-mini`, `gpt-4.1-mini`, `gpt-5.4-mini`, and newer listed models as of the local CLI check on 2026-04-24.
- Do not store Azure API keys in repo files. Retrieve keys via CLI only when configuring local runtime, Key Vault, or explicit user-approved deployment flow.
