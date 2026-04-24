$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "dashboard")

if (-not (Test-Path "node_modules")) {
  npm ci
}

npx vite --host 0.0.0.0 --port 5175
