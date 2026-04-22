@echo off
title ESGBuddy

echo Starting ESGBuddy...
echo.

:: Start backend
echo [1/2] Starting backend (FastAPI)...
start "ESGBuddy Backend" cmd /k "cd /d %~dp0backend && venv\Scripts\activate && uvicorn app.main:app --reload --port 8000"

:: Small delay to let backend initialise
timeout /t 3 /nobreak >nul

:: Start frontend
echo [2/2] Starting frontend (React)...
start "ESGBuddy Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ESGBuddy is starting up.
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:3000
echo.
echo Close the two terminal windows to stop the app.
pause
