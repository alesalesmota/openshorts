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
