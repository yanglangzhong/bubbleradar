#!/bin/sh
set -e

# 生产环境启动脚本：先执行 Alembic 迁移，再启动 Uvicorn
echo "Running database migrations..."
alembic upgrade head

echo "Ensuring default admin user exists..."
python scripts/create_admin.py || true

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
