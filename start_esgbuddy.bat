@echo off
REM ESGBuddy - Start Backend and Frontend in separate terminals
setlocal
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

echo Starting ESGBuddy...
echo.

REM Terminal 1: Backend (Python venv + Uvicorn)
start "ESGBuddy Backend" cmd /k "cd /d "%ROOT%\backend" && call venv\Scripts\activate.bat && echo Backend running at http://localhost:8000 && echo API docs: http://localhost:8000/docs && echo. && echo To stop: press Ctrl+C twice, or run stop_esgbuddy.bat && echo. && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a moment so backend starts first
timeout /t 3 /nobreak >nul

REM Terminal 2: Frontend (Node)
start "ESGBuddy Frontend" cmd /k "cd /d "%ROOT%\frontend" && echo Frontend running at http://localhost:3000 && echo. && npm run dev"

echo.
echo Two windows opened:
echo   - ESGBuddy Backend  (port 8000)
echo   - ESGBuddy Frontend (port 3000)
echo.
echo Use stop_esgbuddy.bat to stop both.
