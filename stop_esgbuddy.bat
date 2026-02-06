@echo off
REM ESGBuddy - Stop Backend and Frontend (kill processes on ports 8000 and 3000)
setlocal
echo Stopping ESGBuddy...
echo.

REM Find and kill process on port 8000 (Backend)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo Killing backend (PID %%a)...
    taskkill /F /PID %%a 2>nul
)

REM Find and kill process on port 3000 (Frontend - Vite)
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo Killing frontend (PID %%a)...
    taskkill /F /PID %%a 2>nul
)

echo.
echo ESGBuddy stopped.
pause
