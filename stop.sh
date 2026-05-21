#!/usr/bin/env bash
# DRG-Agent 停止脚本：关闭前端、后端进程与 Docker 容器
# 用法: ./stop.sh        (保留数据卷)
#       ./stop.sh --purge (同时删除数据卷，彻底清理)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo "停止前端 / 后端 / Celery 进程..."
pkill -f "uvicorn main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
pkill -f "celery -A app.tasks" 2>/dev/null || true
rm -f "$ROOT/.run/"*.pid 2>/dev/null || true

if [ "${1:-}" = "--purge" ]; then
  echo "停止并删除 Docker 容器与数据卷..."
  docker compose down -v
  echo "✓ 已彻底清理 (数据卷已删除)"
else
  echo "停止 Docker 容器 (保留数据卷)..."
  docker compose stop
  echo "✓ 已停止 (数据保留；如需彻底清理执行: ./stop.sh --purge)"
fi
