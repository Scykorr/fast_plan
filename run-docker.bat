@echo off
setlocal EnableExtensions
cd /d "%~dp0"

where docker >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker not found. Install Docker Desktop: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop and try again.
    pause
    exit /b 1
)

if not exist "docker-compose.yml" (
    echo [ERROR] docker-compose.yml not found in %~dp0
    pause
    exit /b 1
)

set "MODE=%~1"
if /i "%MODE%"=="start" goto :compose
if /i "%MODE%"=="" goto :update
if /i "%MODE%"=="update" goto :update

echo Usage: run-docker.bat [update ^| start]
echo   update  - git pull + rebuild containers (default)
echo   start   - rebuild/start without git pull
pause
exit /b 1

:update
echo [1/5] Pulling latest code...
git pull --ff-only
if errorlevel 1 (
    echo [WARN] git pull failed — continuing with local code.
)
goto :compose

:compose
echo [2/5] Building and starting containers...
docker compose up -d --build
if errorlevel 1 (
    echo [ERROR] docker compose up failed.
    pause
    exit /b 1
)

echo [3/5] Waiting for services to start...
timeout /t 8 /nobreak >nul

echo [4/5] Checking backend...
docker compose ps backend | findstr /i "Up" >nul 2>&1
if errorlevel 1 (
    echo [WARN] Backend is not running — retrying migrate/start...
    docker compose up -d backend
    timeout /t 5 /nobreak >nul
    docker compose restart frontend
)

echo [5/5] Container status:
docker compose ps

set "FRONTEND_PORT="
for /f "tokens=2 delims=:" %%A in ('docker compose port frontend 80 2^>nul') do set "FRONTEND_PORT=%%A"
if defined FRONTEND_PORT set "FRONTEND_PORT=%FRONTEND_PORT:/=%"

echo.
echo ========================================
echo   Fast Plan (Docker)
echo ========================================
if defined FRONTEND_PORT (
    echo   Frontend: http://127.0.0.1:%FRONTEND_PORT%
) else (
    echo   Frontend: see "docker compose ps" for port
)
echo   Backend:  http://127.0.0.1:8000
echo   Health:   http://127.0.0.1:8000/api/health/
echo.
echo   Update:   run-docker.bat
echo   Start:    run-docker.bat start
echo   Admin:    docker compose exec backend python manage.py createsuperuser
echo.
echo   Do NOT use "docker compose down -v" — it deletes the database.
echo ========================================
echo.

endlocal
