# ESGBuddy - Stop backend/frontend and close their terminal windows
$ErrorActionPreference = 'SilentlyContinue'
$ports = @(8000, 3000)

foreach ($port in $ports) {
    $conn = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if (-not $conn) { continue }

    $pid = $conn.OwningProcess
    $procName = (Get-Process -Id $pid -ErrorAction SilentlyContinue).ProcessName
    Write-Host "Killing process on port $port (PID $pid, $procName)..."
    Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue

    $currentPid = $pid
    for ($i = 0; $i -lt 5; $i++) {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $currentPid" -ErrorAction SilentlyContinue
        if (-not $proc) { break }
        $parentId = $proc.ParentProcessId
        if ($parentId -eq 0) { break }
        $parent = Get-Process -Id $parentId -ErrorAction SilentlyContinue
        if ($parent.ProcessName -eq 'cmd') {
            Write-Host "Closing terminal window (PID $parentId)..."
            Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
            break
        }
        Stop-Process -Id $parentId -Force -ErrorAction SilentlyContinue
        $currentPid = $parentId
    }
}

Write-Host ""
Write-Host "ESGBuddy stopped."
