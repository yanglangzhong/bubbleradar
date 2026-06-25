@echo off
chcp 65001 >nul
echo ============================================
echo  泡沫雷达 — 前端部署脚本
echo ============================================
echo.

set /p API_URL="请输入后端 API 地址 (如 https://api.bubbleradar.com，直接回车使用默认 /api/v1): "

if not "%API_URL%"=="" (
    echo 使用后端地址: %API_URL%
    set "VITE_API_BASE_URL=%API_URL%/api/v1"
) else (
    echo 使用默认后端地址: /api/v1
    set "VITE_API_BASE_URL=/api/v1"
)

echo.
echo 正在构建前端...
cd /d "%~dp0\frontend"

"C:\Program Files\nodejs\npm.cmd" run build

if errorlevel 1 (
    echo.
    echo [错误] 构建失败！
    pause
    exit /b 1
)

echo.
echo ============================================
echo  构建成功！
echo ============================================
echo.
echo 构建产物位于: frontend\dist\
echo.
echo 下一步：
echo 1. 注册 Cloudflare 账号: https://dash.cloudflare.com/sign-up
echo 2. 进入 Pages 控制台 → 创建项目 → 拖拽上传 dist 文件夹
echo 3. 或者使用 Wrangler CLI 部署（见 deploy-frontend.md）
echo.
pause
