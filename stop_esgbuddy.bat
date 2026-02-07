@echo off
REM ESGBuddy - Stop Backend and Frontend (kill processes on ports 8000 and 3000 and close their terminal windows)
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
echo Stopping ESGBuddy...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\stop_esgbuddy.ps1"
echo.
echo ESGBuddy stopped.
