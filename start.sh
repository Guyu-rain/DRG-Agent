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

echo "[1/6] 启动 Docker 服务 (PostgreSQL + Redis)..."
docker compose up -d

echo "[2/6] 等待 PostgreSQL 就绪..."
for _ in $(seq 1 30); do
  if docker exec drg-agent-postgres pg_isready -U drgagent -d drg_agent >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

echo "[3/6] 应用数据库迁移 (alembic upgrade head)..."
( cd server && "$VENV/bin/alembic" upgrade head )

echo "[4/6] 启动后端 FastAPI (:8000)..."
( cd server && nohup "$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8000 \
    > "$ROOT/logs/backend.log" 2>&1 & echo $! > "$ROOT/.run/backend.pid" )

echo "[5/6] 启动前端 Vite (:5173)..."
( cd web && nohup corepack pnpm dev \
    > "$ROOT/logs/frontend.log" 2>&1 & echo $! > "$ROOT/.run/frontend.pid" )

echo "[6/6] 等待后端健康检查并初始化演示数据..."
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
echo "  日志:      logs/backend.log  logs/frontend.log"
echo "  停止:      ./stop.sh"
echo ""
echo "提示: 文档/测试用例的异步任务如需 Celery worker，请另开终端执行："
echo "  cd server && ../.venv/bin/celery -A app.tasks worker --loglevel=info"
