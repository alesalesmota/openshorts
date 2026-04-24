param(
  [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location (Join-Path $Root "render-service")

if (-not $SkipInstall -and -not (Test-Path "node_modules")) {
  npm ci
}

npm run build
npm start
