param(
  [string]$Location = "eastus"
)

$ErrorActionPreference = "Stop"
$Az = "C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

& $Az account show --output table
& $Az vm list-usage --location $Location --output table
