#!/bin/bash
set -euo pipefail

# ============================================================
# Docker 容器独立启动脚本（不使用 docker-compose）
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

IMAGE_NAME="inspection-app:latest"
NETWORK_NAME="inspection-network"

# 容器名称
POSTGRES_CONTAINER="inspection-postgres-standalone"
REDIS_CONTAINER="inspection-redis-standalone"
API_CONTAINER="inspection-api-standalone"
WORKER_CONTAINER="inspection-worker-standalone"
BEAT_CONTAINER="inspection-beat-standalone"

# 数据库配置
DB_USER="inspector"
DB_PASSWORD="password"
DB_NAME="inspection"

echo "=========================================="
echo "Docker 独立容器启动脚本"
echo "=========================================="

# 检查镜像是否存在
if ! docker images "${IMAGE_NAME}" | grep -q "inspection-app"; then
    echo "❌ 错误: 镜像 ${IMAGE_NAME} 不存在"
    echo "请先运行: ./build-docker.sh"
    exit 1
fi

# 检查 .env 文件
if [ ! -f "backend/.env" ]; then
    echo "❌ 错误: backend/.env 不存在"
    echo "请从 backend/.env.example 复制并配置"
    exit 1
fi

# 创建 Docker 网络
echo ""
echo "📡 创建 Docker 网络: ${NETWORK_NAME}"
docker network create "${NETWORK_NAME}" 2>/dev/null || echo "网络已存在，跳过创建"

# 启动 PostgreSQL
echo ""
echo "🐘 启动 PostgreSQL..."
docker run -d \
    --name "${POSTGRES_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    -e POSTGRES_USER="${DB_USER}" \
    -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
    -e POSTGRES_DB="${DB_NAME}" \
    -p 5432:5432 \
    --restart unless-stopped \
    postgres:15-alpine

# 等待 PostgreSQL 就绪
echo "等待 PostgreSQL 启动..."
for i in {1..30}; do
    if docker exec "${POSTGRES_CONTAINER}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
        echo "✅ PostgreSQL 已就绪"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ PostgreSQL 启动超时"
        exit 1
    fi
    sleep 1
done

# 启动 Redis
echo ""
echo "🔴 启动 Redis..."
docker run -d \
    --name "${REDIS_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    -p 6379:6379 \
    --restart unless-stopped \
    redis:7-alpine redis-server --appendonly yes

# 等待 Redis 就绪
echo "等待 Redis 启动..."
for i in {1..15}; do
    if docker exec "${REDIS_CONTAINER}" redis-cli ping >/dev/null 2>&1; then
        echo "✅ Redis 已就绪"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "❌ Redis 启动超时"
        exit 1
    fi
    sleep 1
done

# 执行数据库迁移
echo ""
echo "🔄 执行数据库迁移..."
docker run --rm \
    --name inspection-migrate-temp \
    --network "${NETWORK_NAME}" \
    --env-file backend/.env \
    -e DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${POSTGRES_CONTAINER}:5432/${DB_NAME}" \
    -e REDIS_URL="redis://${REDIS_CONTAINER}:6379/0" \
    "${IMAGE_NAME}" \
    alembic upgrade head

if [ $? -ne 0 ]; then
    echo "❌ 数据库迁移失败"
    exit 1
fi
echo "✅ 数据库迁移完成"

# 启动 API 服务
echo ""
echo "🚀 启动 API 服务..."
docker run -d \
    --name "${API_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    --env-file backend/.env \
    -e DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${POSTGRES_CONTAINER}:5432/${DB_NAME}" \
    -e REDIS_URL="redis://${REDIS_CONTAINER}:6379/0" \
    -p 8000:8000 \
    --restart unless-stopped \
    "${IMAGE_NAME}" \
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2

# 启动 Celery Worker
echo ""
echo "⚙️  启动 Celery Worker..."
docker run -d \
    --name "${WORKER_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    --env-file backend/.env \
    -e DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${POSTGRES_CONTAINER}:5432/${DB_NAME}" \
    -e REDIS_URL="redis://${REDIS_CONTAINER}:6379/0" \
    --restart unless-stopped \
    "${IMAGE_NAME}" \
    celery -A app.tasks.celery_app.celery worker -l info --concurrency 4

# 启动 Celery Beat
echo ""
echo "⏰ 启动 Celery Beat..."
docker run -d \
    --name "${BEAT_CONTAINER}" \
    --network "${NETWORK_NAME}" \
    --env-file backend/.env \
    -e DATABASE_URL="postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${POSTGRES_CONTAINER}:5432/${DB_NAME}" \
    -e REDIS_URL="redis://${REDIS_CONTAINER}:6379/0" \
    --restart unless-stopped \
    "${IMAGE_NAME}" \
    celery -A app.tasks.celery_app.celery beat -l info

echo ""
echo "=========================================="
echo "✅ 所有服务启动完成!"
echo "=========================================="
echo ""
echo "服务访问地址:"
echo "  API:        http://localhost:8000"
echo "  API 文档:   http://localhost:8000/docs"
echo "  PostgreSQL: localhost:5432"
echo "  Redis:      localhost:6379"
echo ""
echo "查看日志:"
echo "  API:    docker logs -f ${API_CONTAINER}"
echo "  Worker: docker logs -f ${WORKER_CONTAINER}"
echo "  Beat:   docker logs -f ${BEAT_CONTAINER}"
echo ""
echo "停止所有服务:"
echo "  docker stop ${API_CONTAINER} ${WORKER_CONTAINER} ${BEAT_CONTAINER} ${POSTGRES_CONTAINER} ${REDIS_CONTAINER}"
echo ""
echo "删除所有容器:"
echo "  docker rm ${API_CONTAINER} ${WORKER_CONTAINER} ${BEAT_CONTAINER} ${POSTGRES_CONTAINER} ${REDIS_CONTAINER}"
echo ""
