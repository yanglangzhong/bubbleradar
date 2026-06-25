@echo off
setlocal EnableDelayedExpansion
title BubbleRadar Frontend

echo ==========================================
echo  BubbleRadar Frontend
echo ==========================================

set "FRONTEND_DIR=%~dp0frontend"
cd /d "%FRONTEND_DIR%"

:: Check Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found in PATH.
    echo [HINT] Please install Node.js from https://nodejs.org
    pause
    exit /b 1
)

:: Locate npm-cli.js (avoid calling npm.cmd from batch, which can resolve paths incorrectly)
set "NPM_CLI_JS=C:\Program Files\nodejs\node_modules\npm\bin\npm-cli.js"
if not exist "!NPM_CLI_JS!" (
    for /f "delims=" %%a in ('where node') do (
        set "NODE_DIR=%%~dpa"
        set "NPM_CLI_JS=%%~dpanode_modules\npm\bin\npm-cli.js"
        if exist "!NPM_CLI_JS!" goto :npm_found
    )
    echo [ERROR] npm-cli.js not found. Please reinstall Node.js.
    pause
    exit /b 1
)
:npm_found

if not exist "%FRONTEND_DIR%\node_modules" (
    echo [2/2] node_modules missing, installing...
    node "!NPM_CLI_JS!" install
    if errorlevel 1 (
        echo [ERROR] npm install failed.
        pause
        exit /b 1
    )
) else (
    echo [2/2] node_modules ready.
)

echo.
echo Starting Vite dev server...
echo     URL: http://localhost:5173
echo.

:: Run Vite directly to avoid npm.cmd path-resolution issues when called from batch
node "%FRONTEND_DIR%\node_modules\vite\bin\vite.js"

if errorlevel 1 (
    echo.
    echo [ERROR] Frontend failed to start.
    pause
)
