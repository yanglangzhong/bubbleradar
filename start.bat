@echo off
chcp 65001 >nul 2>&1
title BubbleRadar Launcher

setlocal EnableDelayedExpansion

set "PROJECT_DIR=%~dp0"
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"
set "BACKEND_DIR=%PROJECT_DIR%\backend"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "BACKEND_BAT=%PROJECT_DIR%\start-backend.bat"
set "FRONTEND_BAT=%PROJECT_DIR%\start-frontend.bat"

cls
echo ==========================================
echo  BubbleRadar Launcher
echo ==========================================
echo.
echo Project: %PROJECT_DIR%
echo Backend: %BACKEND_DIR%
echo Frontend: %FRONTEND_DIR%
echo.

if not exist "%BACKEND_DIR%" (
    echo [ERROR] Backend directory not found: %BACKEND_DIR%
    pause
    exit /b 1
)

if not exist "%FRONTEND_DIR%" (
    echo [ERROR] Frontend directory not found: %FRONTEND_DIR%
    pause
    exit /b 1
)

if not exist "%BACKEND_BAT%" (
    echo [ERROR] %BACKEND_BAT% not found.
    pause
    exit /b 1
)

if not exist "%FRONTEND_BAT%" (
    echo [ERROR] %FRONTEND_BAT% not found.
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  Starting services...
echo ==========================================
echo.

:: Start backend in a new window
echo [1/2] Starting backend...
start "BubbleRadar Backend" "%BACKEND_BAT%"
if errorlevel 1 (
    echo [ERROR] Failed to start backend.
    pause
    exit /b 1
)

:: Wait for backend to be ready
echo         Waiting for backend http://localhost:8000 ...
set /a attempts=0
set "BACKEND_READY=0"
:wait_backend
set /a attempts+=1
timeout /t 1 /nobreak >nul 2>&1
powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1', 8000); exit 0 } catch { exit 1 }" >nul 2>&1
if errorlevel 1 (
    if %attempts% lss 30 goto wait_backend
    echo [WARN] Backend did not respond in 30s, continuing anyway...
) else (
    set "BACKEND_READY=1"
)
if "%BACKEND_READY%"=="1" echo         Backend is ready.

:: Start frontend in a new window
echo [2/2] Starting frontend...
start "BubbleRadar Frontend" "%FRONTEND_BAT%"
if errorlevel 1 (
    echo [ERROR] Failed to start frontend.
    pause
    exit /b 1
)

timeout /t 2 /nobreak >nul 2>&1

echo.
echo ==========================================
echo  Services started
echo ==========================================
echo [OK] Backend  http://localhost:8000
echo [OK] Frontend http://localhost:5173
echo.
echo Open browser:
echo   http://localhost:5173        (Dashboard)
echo   http://localhost:8000/api/docs (API Docs)
echo.
echo ==========================================
echo.

pause
endlocal
