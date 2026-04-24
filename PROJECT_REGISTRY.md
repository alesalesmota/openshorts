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
- Docker is not currently available on this computer PATH, so the documented full-stack launch command `docker compose up --build` cannot run yet.

## Runtime Notes

- README expects Docker and Docker Compose for normal use.
- Main dashboard URL after Docker launch: `http://localhost:5175`.
- AI/video workflows require external API keys such as Gemini, fal.ai, ElevenLabs, and optionally Upload-Post/AWS S3 depending on feature.

## Product Direction Notes

- Current intended direction is to narrow the app toward long-form video cutting and editing workflows.
- Priority feature area: Clip Generator / long video to short clips.
- AI Shorts with generated actors is not the current focus.
- ElevenLabs and fal.ai should not be treated as required for the focused Clip Generator workflow.
- Upload-Post remains in scope for publishing finished clips to TikTok, Instagram Reels, and YouTube Shorts.
- AWS S3 should remain optional; local-first output is preferred for lightweight use.

## Architecture Observations

- The current Clip Generator depends directly on Gemini in `main.py` for viral moment selection and clip metadata.
- The frontend currently labels and requires a Gemini API key for Clip Generator.
- Future model work should add an API/provider abstraction before adding more models, so Gemini is one provider instead of the app contract.
- The first multi-provider target should be transcript-to-clips analysis, because that is the core long-video cutting decision point.
- Keep Upload-Post integration separate from AI provider work; publishing is a downstream workflow and should not affect clip detection.

## Lightweight Local Run Notes

- Rancher Desktop was installed as a Docker-compatible option, but WSL/Rancher consumed about 7.9 GB RAM during setup/build.
- Rancher/WSL is currently stopped.
- Preferred exploration path for this computer is native local run without Docker:
  - dashboard via Vite on `http://localhost:5175`
  - backend via Python/FastAPI on `http://localhost:8000`
  - renderer via Node on `http://localhost:3100` only when needed
- FFmpeg and ffprobe are installed globally through Scoop.

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
