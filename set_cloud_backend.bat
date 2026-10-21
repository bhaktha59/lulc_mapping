@echo off
title Link Cloud Backend and Deploy to Cloudflare
echo =====================================================================
echo  Connecting LULC Frontend to Hosted Cloud Backend
echo =====================================================================
echo.

cd /d "%~dp0"

set "BACKEND_URL=%~1"
if "%BACKEND_URL%"=="" (
    set /p "BACKEND_URL=Enter your hosted Backend API URL (e.g. https://lulc-mapping-api.onrender.com/api): "
)

if "%BACKEND_URL%"=="" (
    echo [ERROR] No Backend URL provided. Aborting.
    pause
    exit /b 1
)

:: Ensure URL ends with /api if not already present
echo %BACKEND_URL% | findstr /i "/api" >nul
if %errorlevel% neq 0 (
    if "%BACKEND_URL:~-1%"=="/" (
        set "BACKEND_URL=%BACKEND_URL%api"
    ) else (
        set "BACKEND_URL=%BACKEND_URL%/api"
    )
)

echo.
echo [1/3] Updating frontend\.env.production with live endpoint:
echo       VITE_API_BASE_URL=%BACKEND_URL%
echo VITE_API_BASE_URL=%BACKEND_URL%> frontend\.env.production

echo.
echo [2/3] Building production frontend with Vite...
call npm run build --prefix frontend
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed.
    pause
    exit /b %errorlevel%
)

echo.
echo [3/3] Deploying updated frontend to Cloudflare (https://lulc.bakthageo59.workers.dev)...
call npx -y wrangler deploy
if %errorlevel% neq 0 (
    echo [ERROR] Cloudflare deploy failed.
    pause
    exit /b %errorlevel%
)

echo.
echo =====================================================================
echo  SUCCESS! Your web GIS application is now live and fully independent!
echo  Public Frontend: https://lulc.bakthageo59.workers.dev
echo  Hosted Backend:  %BACKEND_URL%
echo =====================================================================
pause
