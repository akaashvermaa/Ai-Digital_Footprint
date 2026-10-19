@echo off
rem Stops the backend (port 8000) and the frontend (port 5173) started by start.bat
echo Stopping the app...
powershell -NoProfile -Command "foreach ($port in 8000, 5173) { Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue } }"
echo Done.
timeout /t 2 >nul
