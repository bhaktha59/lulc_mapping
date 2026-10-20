@echo off
title Cloudflare Tunnel - LULC Backend Exposer
echo =====================================================================
echo  Starting Cloudflare Tunnel for LULC Backend (Port 8001)
echo =====================================================================
echo.
echo Launching Cloudflare Tunnel to provide free public HTTPS URL...
echo Look for the URL ending with '.trycloudflare.com' below!
echo.
cd /d "%~dp0"
if not exist "cloudflared.exe" (
    echo [ERROR] cloudflared.exe not found in this folder.
    pause
    exit /b 1
)
cloudflared.exe tunnel --url http://127.0.0.1:8001
pause
