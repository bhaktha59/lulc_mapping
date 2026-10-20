@echo off
title LULC Mapping Portal - Launcher
echo =====================================================================
echo  Starting LULC Mapping System (Backend + Frontend)
echo =====================================================================
echo.
echo [1/2] Launching Python FastAPI Backend Server on Port 8001...
start "TN-LULC-Backend-8001" cmd /k "cd /d "%~dp0" && python backend\app.py"
timeout /t 2 >nul

echo [2/2] Launching React Vite Frontend Dev Server on Port 5174...
start "TN-LULC-Frontend-5174" cmd /k "cd /d "%~dp0" && npm run dev"

echo.
echo =====================================================================
echo  Both services launched in separate windows!
echo  - Backend API: http://127.0.0.1:8001/api/health
echo  - Frontend UI: http://127.0.0.1:5174
echo =====================================================================
echo You can keep this launcher closed or open.
pause
