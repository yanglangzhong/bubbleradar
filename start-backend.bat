@echo off
title BubbleRadar Backend

echo ==========================================
echo  BubbleRadar Backend
echo ==========================================

set "BACKEND_DIR=%~dp0backend"
cd /d "%BACKEND_DIR%"

python --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python not found. Please install Python.
        pause
        exit /b 1
    )
    set "PYTHON_CMD=py"
) else (
    set "PYTHON_CMD=python"
)

if not exist "%BACKEND_DIR%\.env" (
    echo [WARN] backend\.env not found.
    echo [HINT] Copy backend\.env.example to backend\.env and fill in your API keys.
    echo.
)

echo [1/2] Starting FastAPI backend...
echo     URL: http://localhost:8000
echo     API Docs: http://localhost:8000/api/docs
echo.

%PYTHON_CMD% run.py

if errorlevel 1 (
    echo.
    echo [ERROR] Backend failed to start.
    pause
)
