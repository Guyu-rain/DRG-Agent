#!/usr/bin/env bash
# DRG-Agent 一键启动脚本：Docker 服务 + 后端 (FastAPI) + 前端 (Vite)
# 用法: ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"
mkdir -p logs .run

VENV="$ROOT/.venv"
if [ ! -x "$VENV/bin/uvicorn" ]; then
  echo "✗ 未找到 Python 虚拟环境 (.venv)，请先在仓库根目录执行: uv sync"
  exit 1
fi

echo "[1/7] 启动 Docker 服务 (PostgreSQL + Redis)..."
docker compose up -d

echo "[2/7] 等待 PostgreSQL 就绪..."
for _ in $(seq 1 30); do
  if docker exec drg-agent-postgres pg_isready -U drgagent -d drg_agent >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[3/7] 应用数据库迁移 (alembic upgrade head)..."
( cd server && "$VENV/bin/alembic" upgrade head )

find_project_pid() {
  pgrep -f "$1" 2>/dev/null | head -n 1 || true
}

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

echo "[4/7] 启动后端 FastAPI (:8000)..."
BACKEND_PID="$(find_project_pid "$VENV/bin/uvicorn main:app.*--port 8000")"
if [ -n "$BACKEND_PID" ]; then
  echo "$BACKEND_PID" > "$ROOT/.run/backend.pid"
  echo "  后端已运行 (PID $BACKEND_PID)，跳过重复启动"
elif port_in_use 8000; then
  echo "✗ 端口 8000 已被其他程序占用，已停止启动以避免连接到错误后端"
  exit 1
else
  ( cd server && nohup "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 \
      > "$ROOT/logs/backend.log" 2>&1 & echo $! > "$ROOT/.run/backend.pid" )
fi

echo "[5/7] 启动 Celery worker..."
CELERY_PID="$(find_project_pid "$VENV/bin/celery -A app.tasks worker")"
if [ -n "$CELERY_PID" ]; then
  echo "$CELERY_PID" > "$ROOT/.run/celery.pid"
  echo "  Celery 已运行 (PID $CELERY_PID)，跳过重复启动"
else
  ( cd server && nohup "$VENV/bin/celery" -A app.tasks worker --pool=solo --loglevel=info \
      > "$ROOT/logs/celery.log" 2>&1 & echo $! > "$ROOT/.run/celery.pid" )
fi

echo "[6/7] 启动前端 Vite (:5173)..."
FRONTEND_PID="$(find_project_pid "$ROOT/web/node_modules/.*/vite.*--host")"
if [ -n "$FRONTEND_PID" ]; then
  echo "$FRONTEND_PID" > "$ROOT/.run/frontend.pid"
  echo "  前端已运行 (PID $FRONTEND_PID)，跳过重复启动"
elif port_in_use 5173; then
  echo "✗ 端口 5173 已被其他程序占用，已停止启动以避免自动漂移到其他端口"
  exit 1
else
  ( cd web && nohup corepack pnpm dev \
      > "$ROOT/logs/frontend.log" 2>&1 & echo $! > "$ROOT/.run/frontend.pid" )
fi

echo "[7/7] 等待后端健康检查并初始化演示数据..."
for _ in $(seq 1 40); do
  if curl -sf http://localhost:8000/api/v1/system/health >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
curl -s -X POST http://localhost:8000/api/v1/system/demo/init >/dev/null || true

echo ""
echo "✓ DRG-Agent 已启动"
echo "  前端:      http://localhost:5173"
echo "  后端 API:  http://localhost:8000"
echo "  API 文档:  http://localhost:8000/docs"
echo "  日志:      logs/backend.log  logs/celery.log  logs/frontend.log"
echo "  停止:      ./stop.sh"
