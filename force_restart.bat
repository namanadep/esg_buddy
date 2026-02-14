@echo off
echo Forcefully restarting ESGBuddy...
echo.

REM Kill everything on port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do (
    echo Killing process %%a on port 8000...
    taskkill /F /PID %%a 2>nul
)

REM Kill everything on port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000" ^| findstr "LISTENING"') do (
    echo Killing process %%a on port 3000...
    taskkill /F /PID %%a 2>nul
)

echo.
echo Waiting 3 seconds...
timeout /t 3 /nobreak >nul

echo.
echo Starting ESGBuddy...
start "ESGBuddy Backend" cmd /k "cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak >nul
start "ESGBuddy Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ESGBuddy restarted!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
echo.
