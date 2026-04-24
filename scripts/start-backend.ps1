param(
  [switch]$Install,
  [switch]$UseVenv
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $Root

$Python = "python"

if ($UseVenv) {
  if (-not (Test-Path ".venv")) {
    py -3.11 -m venv .venv
  }
  $Python = ".\.venv\Scripts\python.exe"
}

if ($Install) {
  & $Python -m pip install --upgrade pip
  & $Python -m pip install -r requirements.txt
}

if (-not $env:RENDER_SERVICE_URL) {
  $env:RENDER_SERVICE_URL = "http://localhost:3100"
}

& $Python -m uvicorn app:app --host 0.0.0.0 --port 8000
