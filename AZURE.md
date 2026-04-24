# Azure Notes

Azure is intended for heavy video processing when local execution is too slow or uses too much RAM.

## Current Access

Azure CLI is installed locally and authenticated through interactive `az login`.

Check the active account:

```powershell
& 'C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd' account show
```

## Resource Defaults

- Resource group: `rg-openshorts`
- Preferred region: `eastus`
- Storage: Azure Blob for optional input/output files
- Compute: GPU VM when quota allows; CPU VM fallback

Do not store raw Azure secrets in repo files.

## Cost Rules

- Check quota before creating GPU resources.
- Stop or delete compute after test jobs.
- Prefer small CPU resources for API/frontend and reserve GPU for worker jobs.

## Useful Commands

```powershell
.\scripts\azure\check-quota.ps1
```

```powershell
.\scripts\azure\create-resource-group.ps1
```
