@echo off
setlocal

cd /d "%~dp0"

where pwsh >nul 2>nul
if %ERRORLEVEL%==0 (
  pwsh -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-codex-dev.ps1" %*
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start-codex-dev.ps1" %*
)

set "EXIT_CODE=%ERRORLEVEL%"
echo.

if not "%EXIT_CODE%"=="0" (
  echo OpenShorts failed to start. Check the output above and logs in %%TEMP%%\openshorts-codex.
  echo.
)

echo Press any key to close this window.
pause >nul
exit /b %EXIT_CODE%
