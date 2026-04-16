#!/bin/bash
set -euo pipefail

# ============================================================
# Docker 镜像一键构建脚本
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="inspection-app"
IMAGE_TAG="latest"

echo "=========================================="
echo "开始构建 Docker 镜像"
echo "=========================================="

# 检查 Dockerfile 是否存在
if [ ! -f "backend/Dockerfile" ]; then
    echo "❌ 错误: backend/Dockerfile 不存在"
    exit 1
fi

# 检查 requirements.txt 是否存在
if [ ! -f "backend/requirements.txt" ]; then
    echo "❌ 错误: backend/requirements.txt 不存在"
    exit 1
fi

echo ""
echo "📦 构建镜像: ${IMAGE_NAME}:${IMAGE_TAG}"
echo ""

# 构建镜像
docker build \
    -t "${IMAGE_NAME}:${IMAGE_TAG}" \
    -f backend/Dockerfile \
    backend/

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ 镜像构建成功!"
    echo "=========================================="
    echo ""
    echo "镜像信息:"
    docker images "${IMAGE_NAME}:${IMAGE_TAG}"
    echo ""
    echo "下一步:"
    echo "  1. 使用 docker-compose: docker-compose up -d"
    echo "  2. 使用独立脚本: ./run-docker.sh"
else
    echo ""
    echo "❌ 镜像构建失败"
    exit 1
fi
