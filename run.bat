@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Fast Plan — launcher
echo ========================================
echo   Fast Plan — one-click start
echo ========================================
echo.

REM --- Node.js on PATH (common Windows install) ---
if exist "C:\Program Files\nodejs\npm.cmd" (
    set "PATH=C:\Program Files\nodejs;%PATH%"
)
if exist "%LOCALAPPDATA%\Programs\node\npm.cmd" (
    set "PATH=%LOCALAPPDATA%\Programs\node;%PATH%"
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js LTS: https://nodejs.org/
    pause
    exit /b 1
)

where py >nul 2>&1
if not errorlevel 1 (
    set "PY=py -3"
) else (
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Install Python 3.12+: https://www.python.org/
        pause
        exit /b 1
    )
    set "PY=python"
)

REM --- [1] Virtualenv ---
if not exist "venv\Scripts\python.exe" (
    echo [1/6] Creating venv...
    %PY% -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv.
        pause
        exit /b 1
    )
) else (
    echo [1/6] venv OK
)

set "VENV_PY=%~dp0venv\Scripts\python.exe"
set "VENV_PIP=%~dp0venv\Scripts\pip.exe"

REM --- [2] Python deps ---
echo [2/6] Checking Python packages...
"%VENV_PY%" -c "import django, rest_framework" >nul 2>&1
if errorlevel 1 (
    echo Installing requirements.txt ...
    "%VENV_PIP%" install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] pip install failed.
        pause
        exit /b 1
    )
)

REM --- [3] Frontend deps ---
echo [3/6] Checking frontend packages...
if not exist "frontend\node_modules\" (
    echo Running npm install ...
    pushd frontend
    call npm install
    if errorlevel 1 (
        popd
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
    popd
)

REM --- [4] Free ports ---
echo [4/6] Freeing ports 5173 and 8000 if busy...
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":5173" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
for /f "tokens=5" %%P in ('netstat -ano ^| findstr ":8000" ^| findstr "LISTENING"') do (
    taskkill /PID %%P /F >nul 2>&1
)
timeout /t 1 /nobreak >nul

REM --- [5] Migrations ---
echo [5/6] Applying migrations...
"%VENV_PY%" backend\manage.py migrate --noinput
if errorlevel 1 (
    echo [ERROR] Migrations failed.
    pause
    exit /b 1
)

REM --- [6] Start services ---
echo [6/6] Starting backend + frontend...
start "Fast Plan - Backend" cmd /k "cd /d "%~dp0backend" && "%VENV_PY%" manage.py runserver"
timeout /t 2 /nobreak >nul
start "Fast Plan - Frontend" cmd /k "cd /d "%~dp0frontend" && npm run dev"
timeout /t 3 /nobreak >nul

start "" "http://127.0.0.1:5173"

echo.
echo ========================================
echo   Fast Plan is starting
echo ========================================
echo   Site:     http://127.0.0.1:5173
echo   API:      http://127.0.0.1:8000
echo.
echo   Branch:   stay on feature/ladya-hub for Ladya Hub
echo   Stop:     close Backend and Frontend windows
echo   Docker:   run-docker.bat
echo ========================================
echo.
endlocal
