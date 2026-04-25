param(
  [switch]$NoRestart,
  [switch]$NoAzure
)

$ErrorActionPreference = "Stop"

$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$LogDir = Join-Path $env:TEMP "openshorts-codex"
$BackendOut = Join-Path $LogDir "backend.out.log"
$BackendErr = Join-Path $LogDir "backend.err.log"
$DashboardOut = Join-Path $LogDir "dashboard.out.log"
$DashboardErr = Join-Path $LogDir "dashboard.err.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Stop-PortListener {
  param([int]$Port)

  $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
  foreach ($listener in $listeners) {
    $ownerPid = $listener.OwningProcess
    if ($ownerPid -and $ownerPid -ne $PID) {
      try {
        Stop-Process -Id $ownerPid -Force -ErrorAction Stop
        Write-Host "Stopped existing process $ownerPid on port $Port."
      } catch {
        Write-Warning "Could not stop process $ownerPid on port ${Port}: $($_.Exception.Message)"
      }
    }
  }
}

function Wait-Http {
  param(
    [string]$Url,
    [string]$Name,
    [int]$Attempts = 45
  )

  for ($i = 1; $i -le $Attempts; $i++) {
    try {
      $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
      if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
        Write-Host "$Name ready: $Url"
        return
      }
    } catch {
      Start-Sleep -Seconds 1
    }
  }

  throw "$Name did not become ready at $Url. Check logs in $LogDir."
}

if (-not $NoRestart) {
  Stop-PortListener -Port 8000
  Stop-PortListener -Port 5175
}

Remove-Item -LiteralPath $BackendOut, $BackendErr, $DashboardOut, $DashboardErr -ErrorAction SilentlyContinue

$PowerShellExe = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $PowerShellExe) {
  $PowerShellExe = (Get-Command powershell -ErrorAction Stop).Source
}

$AzureSetup = @'
if (-not $env:RENDER_SERVICE_URL) {
  $env:RENDER_SERVICE_URL = "http://localhost:3100"
}

if (-not $env:AI_PROVIDER) {
  $env:AI_PROVIDER = "azure-openai"
}
if (-not $env:AI_MODEL) {
  $env:AI_MODEL = "openshorts-gpt-4-1-mini"
}
if (-not $env:AZURE_OPENAI_ENDPOINT) {
  $env:AZURE_OPENAI_ENDPOINT = "https://blue-008-36-2109-resource.cognitiveservices.azure.com/"
}
if (-not $env:AZURE_OPENAI_DEPLOYMENT) {
  $env:AZURE_OPENAI_DEPLOYMENT = "openshorts-gpt-4-1-mini"
}
if (-not $env:AZURE_OPENAI_API_VERSION) {
  $env:AZURE_OPENAI_API_VERSION = "2024-10-21"
}
if (-not $env:AZURE_OPENAI_RESOURCE_GROUP) {
  $env:AZURE_OPENAI_RESOURCE_GROUP = "rg-Blue_008_36-2109"
}
if (-not $env:AZURE_OPENAI_ACCOUNT_NAME) {
  $env:AZURE_OPENAI_ACCOUNT_NAME = "blue-008-36-2109-resource"
}

if (-not $env:AI_API_KEY) {
  $az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"
  if (-not (Test-Path -LiteralPath $az)) {
    $azCommand = Get-Command az -ErrorAction SilentlyContinue
    if ($azCommand) {
      $az = $azCommand.Source
    }
  }

  if (Test-Path -LiteralPath $az) {
    try {
      $key = & $az cognitiveservices account keys list --resource-group $env:AZURE_OPENAI_RESOURCE_GROUP --name $env:AZURE_OPENAI_ACCOUNT_NAME --query key1 -o tsv 2>$null
      if ($LASTEXITCODE -eq 0 -and $key) {
        $env:AI_API_KEY = $key.Trim()
      } else {
        Write-Warning "Azure CLI did not return an AI key. Backend will start without a backend AI key."
      }
    } catch {
      Write-Warning "Azure key lookup failed. Backend will start without a backend AI key. $($_.Exception.Message)"
    }
  } else {
    Write-Warning "Azure CLI not found. Backend will start without a backend AI key."
  }
}
'@

if ($NoAzure) {
  $AzureSetup = @'
if (-not $env:RENDER_SERVICE_URL) {
  $env:RENDER_SERVICE_URL = "http://localhost:3100"
}
'@
}

$BackendScript = @"
Set-Location -LiteralPath '$Root'
`$ErrorActionPreference = "Stop"
$AzureSetup
.\scripts\start-backend.ps1
"@

$DashboardScript = @"
Set-Location -LiteralPath '$Root'
`$ErrorActionPreference = "Stop"
.\scripts\start-dashboard.ps1
"@

$BackendEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($BackendScript))
$DashboardEncoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($DashboardScript))

$BackendProcess = Start-Process -FilePath $PowerShellExe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $BackendEncoded) -WindowStyle Hidden -RedirectStandardOutput $BackendOut -RedirectStandardError $BackendErr -PassThru
Start-Sleep -Seconds 2
$DashboardProcess = Start-Process -FilePath $PowerShellExe -ArgumentList @("-NoProfile", "-ExecutionPolicy", "Bypass", "-EncodedCommand", $DashboardEncoded) -WindowStyle Hidden -RedirectStandardOutput $DashboardOut -RedirectStandardError $DashboardErr -PassThru

Wait-Http -Url "http://localhost:8000/api/ai/defaults" -Name "Backend"
Wait-Http -Url "http://localhost:5175/" -Name "Dashboard"

Write-Host ""
Write-Host "OpenShorts local dev ready."
Write-Host "Dashboard: http://localhost:5175"
Write-Host "Backend:   http://localhost:8000"
Write-Host "Renderer:  not started by default"
Write-Host "Logs:      $LogDir"
Write-Host "PIDs:      backend=$($BackendProcess.Id), dashboard=$($DashboardProcess.Id)"
