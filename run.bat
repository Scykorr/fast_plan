@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found: venv\Scripts\python.exe
    echo Create venv and install dependencies: pip install -r requirements.txt
    pause
    exit /b 1
)

if not exist "frontend\package.json" (
    echo [ERROR] Frontend not found: frontend\package.json
    pause
    exit /b 1
)

echo [1/3] Applying database migrations...
venv\Scripts\python.exe backend\manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Migrations failed.
    pause
    exit /b 1
)

if exist "C:\Program Files\nodejs\npm.cmd" (
    set "PATH=C:\Program Files\nodejs;%PATH%"
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js: https://nodejs.org/
    pause
    exit /b 1
)

echo [2/3] Starting backend (Django)...
start "Fast Plan - Backend" cmd /k "cd /d "%~dp0backend" && "%~dp0venv\Scripts\python.exe" manage.py runserver"

timeout /t 2 /nobreak >nul

echo [3/3] Starting frontend (Vite)...
start "Fast Plan - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo ========================================
echo   Fast Plan is starting
echo ========================================
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:5173
echo.
echo   Close Backend and Frontend windows to stop.
echo ========================================
echo.

endlocal
