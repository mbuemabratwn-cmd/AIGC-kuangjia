@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found. Install Python 3.11+ and re-run this file.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js / npm was not found. Install Node.js LTS and re-run this file.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo [SETUP] Creating Python virtual environment...
  python -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Failed to create Python virtual environment.
    pause
    exit /b 1
  )
)

echo [SETUP] Installing backend dependencies...
".venv\Scripts\python.exe" -m pip install -r "apps\api\requirements.txt"
if errorlevel 1 (
  echo [ERROR] Failed to install backend dependencies.
  pause
  exit /b 1
)

if not exist "apps\web\node_modules" (
  echo [SETUP] Installing frontend dependencies...
  pushd "apps\web"
  call npm install
  if errorlevel 1 (
    popd
    echo [ERROR] Failed to install frontend dependencies.
    pause
    exit /b 1
  )
  popd
)

if not exist "data" mkdir "data"
if not exist "data\generated" mkdir "data\generated"
if not exist "data\reference-assets" mkdir "data\reference-assets"

echo [START] Backend: http://127.0.0.1:38381
start "AIGC Backend" cmd /k "cd /d %~dp0apps\api && set AIGC_LOCAL_API_BASE_URL=http://127.0.0.1:38381&& ..\..\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 38381"

echo [START] Frontend: http://127.0.0.1:5173
start "AIGC Frontend" cmd /k "cd /d %~dp0apps\web && npm run dev -- --host 127.0.0.1 --port 5173"

timeout /t 3 >nul
start "" "http://127.0.0.1:5173"

echo.
echo AIGC Local Studio is starting.
echo First-time users should open Settings and enter their own API keys.
echo Supabase settings are loaded from apps\api\.env if that file is included.
echo.
pause
