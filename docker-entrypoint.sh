#!/bin/sh
# ============================================================
# Docker 入口脚本 — 初始化知识库并启动 Web 服务
# ============================================================

set -e

echo "========================================="
echo "  DevOps & Infra 知识库"
echo "  Docker Container Starting..."
echo "========================================="

# 初始化知识库目录（幂等操作，已存在则跳过）
echo "[1/2] Initializing knowledge base..."
python kb.py init

# 启动 Web 服务
echo "[2/2] Starting web server on 0.0.0.0:8000..."
exec python kb.py serve --host 0.0.0.0 --port 8000
