@echo off
title Cloudflare Pages - Automated Deployment
echo =====================================================================
echo  Deploying LULC Mapping Frontend to Cloudflare Pages
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/2] Building production frontend bundle with Vite...
call npm run build --prefix frontend
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed. Please check errors above.
    pause
    exit /b %errorlevel%
)
echo [OK] Build completed successfully.
echo.

echo [2/2] Publishing to Cloudflare via Wrangler...
echo Note: If not logged in, Wrangler will open your browser to authorize.
echo.
call npx -y wrangler deploy
echo.
echo =====================================================================
echo  Deployment finished!
echo =====================================================================
pause
