@echo off
setlocal
cd /d "%~dp0"
title Footprint Risk Analyzer - launcher

echo.
echo  Digital Footprint Risk Analyzer
echo  --------------------------------

where python >nul 2>nul
if errorlevel 1 (
  echo  [!] Python is not installed. Install Python 3.10 or newer from https://www.python.org/downloads/
  echo      and tick "Add Python to PATH" in the installer. Then run this file again.
  goto :fail
)
where node >nul 2>nul
if errorlevel 1 (
  echo  [!] Node.js is not installed. Install the LTS version from https://nodejs.org/ and run this file again.
  goto :fail
)

python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
  echo  [!] Your Python is too old. Install Python 3.10 or newer from https://www.python.org/downloads/
  goto :fail
)

netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul
if not errorlevel 1 (
  echo  [!] Port 8000 is already in use. If the app is already running, just open http://127.0.0.1:5173
  echo      Otherwise run stop.bat first, then try again.
  goto :fail
)
netstat -ano | findstr /R /C:":5173 .*LISTENING" >nul
if not errorlevel 1 (
  echo  [!] Port 5173 is already in use. If the app is already running, just open http://127.0.0.1:5173
  echo      Otherwise run stop.bat first, then try again.
  goto :fail
)

rem ---------- first-run setup (skipped on later runs) ----------
if not exist "backend\venv\Scripts\python.exe" (
  echo  [1/4] Creating Python environment...
  python -m venv backend\venv
  if errorlevel 1 goto :fail
)
if not exist "backend\venv\.installed" (
  echo  [2/4] Installing backend libraries. This takes a few minutes the first time...
  "backend\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  "backend\venv\Scripts\python.exe" -m pip install -r backend\requirements.txt
  if errorlevel 1 goto :fail
  "backend\venv\Scripts\python.exe" -m spacy download en_core_web_sm
  if errorlevel 1 goto :fail
  echo ok> "backend\venv\.installed"
)
if not exist "backend\app\models\risk_model.joblib" (
  echo  [3/4] Training the risky-post model...
  pushd backend
  "venv\Scripts\python.exe" train_model.py
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
)
if not exist "frontend\node_modules" (
  echo  [4/4] Installing frontend libraries...
  pushd frontend
  call npm install
  if errorlevel 1 (
    popd
    goto :fail
  )
  popd
)

rem ---------- launch ----------
echo.
echo  Starting the app...
start "Footprint backend (close to stop)" /D "%~dp0backend" cmd /k ""venv\Scripts\python.exe" -W ignore -m uvicorn app.main:app --port 8000"
start "Footprint frontend (close to stop)" /D "%~dp0frontend" cmd /k "npm run dev -- --port 5173 --strictPort"

powershell -NoProfile -Command "for ($i = 0; $i -lt 90; $i++) { try { Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/api/health -TimeoutSec 2 | Out-Null; Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5173 -TimeoutSec 2 | Out-Null; exit 0 } catch { Start-Sleep -Seconds 1 } }; exit 1"
if errorlevel 1 (
  echo  [!] The app did not start. Look at the two black windows that opened for the error message.
  goto :fail
)

start "" http://127.0.0.1:5173
echo.
echo  The app is running at http://127.0.0.1:5173
echo  To stop it, close the two black windows (or run stop.bat).
echo.
pause
exit /b 0

:fail
echo.
echo  Something went wrong. Read the message above, fix it, and run start.bat again.
pause
exit /b 1
