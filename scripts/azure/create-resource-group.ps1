param(
  [string]$Name = "rg-openshorts",
  [string]$Location = "eastus"
)

$ErrorActionPreference = "Stop"
$Az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

& $Az group create --name $Name --location $Location --output table
