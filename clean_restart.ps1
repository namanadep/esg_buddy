# Clean restart script for ESGBuddy
Write-Host "Cleaning up all processes..." -ForegroundColor Yellow

# Get all processes using ports 8000 and 3000
$ports = @(8000, 3000)
foreach ($port in $ports) {
    $connections = netstat -ano | Select-String ":$port.*LISTENING"
    foreach ($conn in $connections) {
        $processId = ($conn -split '\s+')[-1]
        if ($processId -and $processId -ne "0") {
            Write-Host "Killing PID $processId on port $port..." -ForegroundColor Cyan
            try {
                Stop-Process -Id $processId -Force -ErrorAction Stop
                Write-Host "  Killed!" -ForegroundColor Green
            } catch {
                Write-Host "  Failed: $_" -ForegroundColor Red
            }
        }
    }
}

Write-Host "`nWaiting 3 seconds..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# Verify ports are free
Write-Host "`nVerifying ports are free..." -ForegroundColor Yellow
$stillUsed = netstat -ano | Select-String ":(8000|3000).*LISTENING"
if ($stillUsed) {
    Write-Host "WARNING: Some ports still in use:" -ForegroundColor Red
    $stillUsed
} else {
    Write-Host "All ports are free!" -ForegroundColor Green
}

Write-Host "`nStarting ESGBuddy..." -ForegroundColor Yellow
Set-Location $PSScriptRoot

# Start backend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
Write-Host "Backend starting..." -ForegroundColor Cyan

Start-Sleep -Seconds 3

# Start frontend
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm run dev"
Write-Host "Frontend starting..." -ForegroundColor Cyan

Write-Host "`nESGBuddy restarted!" -ForegroundColor Green
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:3000" -ForegroundColor White
Write-Host "`nPress any key to exit..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
