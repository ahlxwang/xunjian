#!/usr/bin/env bash
set -euo pipefail

# 运维巡检系统 - 开发环境一键启动脚本
# 用法: ./dev-start.sh [--skip-deps] [--skip-db]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 解析参数
SKIP_DEPS=false
SKIP_DB=false
for arg in "$@"; do
    case $arg in
        --skip-deps) SKIP_DEPS=true ;;
        --skip-db) SKIP_DB=true ;;
        *) log_error "未知参数: $arg"; exit 1 ;;
    esac
done

# 1. 检查 Python
log_info "检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    log_error "未找到 python3，请先安装 Python 3.11+"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
log_info "Python 版本: $PYTHON_VERSION"

# 2. 检查并安装依赖
if [ "$SKIP_DEPS" = false ]; then
    log_info "安装 Python 依赖..."
    cd "$BACKEND_DIR"
    pip3 install -q -r requirements.txt
    log_info "依赖安装完成"
else
    log_warn "跳过依赖安装 (--skip-deps)"
fi

# 3. 检查 .env 文件
log_info "检查环境变量配置..."
cd "$BACKEND_DIR"
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log_warn ".env 不存在，已从 .env.example 复制，请编辑 backend/.env 填写必要配置后重新运行"
        exit 1
    else
        log_error "未找到 .env 或 .env.example，请先创建 backend/.env"
        exit 1
    fi
fi

# 检查必填项
check_env_var() {
    local var_name="$1"
    local value
    value=$(grep -E "^${var_name}=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$value" ]; then
        log_error "backend/.env 中 ${var_name} 未配置，请填写后重新运行"
        exit 1
    fi
}

check_env_var "DATABASE_URL"
check_env_var "REDIS_URL"
check_env_var "JWT_SECRET"
log_info "环境变量检查通过"

# 4. 启动 PostgreSQL 和 Redis（Docker 方式，如已有外部实例可跳过）
if [ "$SKIP_DB" = false ]; then
    if command -v docker &> /dev/null; then
        log_info "启动 PostgreSQL 容器..."
        if ! docker ps --format '{{.Names}}' | grep -q "^inspection-postgres$"; then
            if docker ps -a --format '{{.Names}}' | grep -q "^inspection-postgres$"; then
                docker start inspection-postgres > /dev/null
            else
                docker run -d --name inspection-postgres \
                    -e POSTGRES_USER=inspector \
                    -e POSTGRES_PASSWORD=password \
                    -e POSTGRES_DB=inspection \
                    -p 5432:5432 postgres:15 > /dev/null
                log_info "等待 PostgreSQL 就绪..."
                sleep 3
            fi
        fi
        log_info "PostgreSQL 已运行"

        log_info "启动 Redis 容器..."
        if ! docker ps --format '{{.Names}}' | grep -q "^inspection-redis$"; then
            if docker ps -a --format '{{.Names}}' | grep -q "^inspection-redis$"; then
                docker start inspection-redis > /dev/null
            else
                docker run -d --name inspection-redis \
                    -p 6379:6379 redis:7 > /dev/null
            fi
        fi
        log_info "Redis 已运行"
    else
        log_warn "未找到 Docker，跳过自动启动 PostgreSQL/Redis，请确保它们已在运行"
    fi
else
    log_warn "跳过数据库启动 (--skip-db)"
fi

# 5. 执行数据库迁移
log_info "执行数据库迁移..."
cd "$BACKEND_DIR"
alembic upgrade head
log_info "数据库迁移完成"

# 6. 清理旧进程
cleanup() {
    log_info "正在关闭所有服务..."
    kill "$API_PID" "$WORKER_PID" "$BEAT_PID" 2>/dev/null || true
    wait "$API_PID" "$WORKER_PID" "$BEAT_PID" 2>/dev/null || true
    log_info "已关闭"
}
trap cleanup EXIT INT TERM

# 7. 启动 API 服务
log_info "启动 API 服务 (端口 8000)..."
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!

# 等待 API 就绪
for i in {1..15}; do
    if curl -sf http://127.0.0.1:8000/health > /dev/null 2>&1; then
        log_info "API 服务已就绪: http://127.0.0.1:8000"
        log_info "Swagger 文档:   http://127.0.0.1:8000/docs"
        break
    fi
    sleep 1
    if [ "$i" -eq 15 ]; then
        log_error "API 服务启动超时，请检查日志"
        exit 1
    fi
done

# 8. 启动 Celery Worker
log_info "启动 Celery Worker..."
cd "$BACKEND_DIR"
celery -A app.tasks.celery_app.celery worker -l info --logfile=/tmp/celery-worker.log &
WORKER_PID=$!

# 9. 启动 Celery Beat（定时任务）
log_info "启动 Celery Beat..."
celery -A app.tasks.celery_app.celery beat -l info --logfile=/tmp/celery-beat.log &
BEAT_PID=$!

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  运维巡检系统已启动${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "  API:     http://127.0.0.1:8000"
echo -e "  文档:    http://127.0.0.1:8000/docs"
echo -e "  Worker:  日志 -> /tmp/celery-worker.log"
echo -e "  Beat:    日志 -> /tmp/celery-beat.log"
echo -e "${GREEN}========================================${NC}"
echo -e "  按 Ctrl+C 停止所有服务"
echo ""

# 等待所有子进程
wait "$API_PID" "$WORKER_PID" "$BEAT_PID"
