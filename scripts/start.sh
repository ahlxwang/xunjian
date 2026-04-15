#!/usr/bin/env bash
set -euo pipefail

# 运维巡检系统 - 一键启动脚本
# 支持 CentOS 7/8 和 Ubuntu 22.04

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 默认配置
DB_CONTAINER_NAME="${DB_CONTAINER_NAME:-postgres-inspection}"
REDIS_CONTAINER_NAME="${REDIS_CONTAINER_NAME:-redis-inspection}"
DB_PORT="${DB_PORT:-5432}"
REDIS_PORT="${REDIS_PORT:-6379}"
API_PORT="${API_PORT:-8000}"

# 数据库配置（从环境变量读取，避免硬编码）
DB_USER="${DB_USER:-inspector}"
DB_PASSWORD="${DB_PASSWORD:-}"
DB_NAME="${DB_NAME:-inspection}"
DB_TEST_NAME="${DB_TEST_NAME:-inspection_test}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_help() {
    cat <<EOF
运维巡检系统 - 一键启动脚本

用法: $0 [选项]

选项:
    --help              显示此帮助信息
    --stop              停止所有服务
    --restart           重启所有服务
    --status            查看服务状态
    --logs              查看服务日志
    --clean             清理容器和数据（危险操作）
    --skip-deps         跳过依赖安装
    --skip-migration    跳过数据库迁移
    --api-only          仅启动 API 服务
    --worker-only       仅启动 Celery Worker
    --beat-only         仅启动 Celery Beat

环境变量:
    DB_PASSWORD         数据库密码（必需）
    DB_USER             数据库用户名（默认: inspector）
    DB_NAME             数据库名称（默认: inspection）
    DB_PORT             数据库端口（默认: 5432）
    REDIS_PORT          Redis 端口（默认: 6379）
    API_PORT            API 端口（默认: 8000）

示例:
    # 完整启动（需要先设置 DB_PASSWORD）
    export DB_PASSWORD="your_secure_password"
    $0

    # 仅启动 API
    $0 --api-only

    # 查看状态
    $0 --status

    # 停止所有服务
    $0 --stop
EOF
}

check_os() {
    if [[ -f /etc/os-release ]]; then
        . /etc/os-release
        OS=$ID
        OS_VERSION=$VERSION_ID
        log_info "检测到操作系统: $OS $OS_VERSION"
    else
        log_error "无法检测操作系统"
        exit 1
    fi
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        echo "CentOS: sudo yum install -y docker && sudo systemctl start docker"
        echo "Ubuntu: sudo apt-get install -y docker.io && sudo systemctl start docker"
        exit 1
    fi

    if ! docker ps &> /dev/null; then
        log_error "Docker 服务未运行或当前用户无权限"
        echo "请运行: sudo systemctl start docker"
        echo "或将当前用户加入 docker 组: sudo usermod -aG docker \$USER"
        exit 1
    fi
    log_info "Docker 检查通过"
}

check_python() {
    local python_cmd=""
    for cmd in python3.11 python3.10 python3 python; do
        if command -v "$cmd" &> /dev/null; then
            local version
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            local major minor
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [[ "$major" -ge 3 && "$minor" -ge 10 ]]; then
                python_cmd="$cmd"
                log_info "找到 Python $version: $cmd"
                break
            fi
        fi
    done

    if [[ -z "$python_cmd" ]]; then
        log_error "未找到 Python 3.10+，请先安装"
        echo "CentOS 8: sudo dnf install -y python3.11"
        echo "Ubuntu:   sudo apt-get install -y python3.11 python3.11-venv"
        exit 1
    fi

    PYTHON_CMD="$python_cmd"
}

check_db_password() {
    if [[ -z "$DB_PASSWORD" ]]; then
        log_error "未设置数据库密码，请设置环境变量 DB_PASSWORD"
        echo "示例: export DB_PASSWORD='your_secure_password'"
        exit 1
    fi
}

setup_venv() {
    local venv_dir="$BACKEND_DIR/.venv"
    if [[ ! -d "$venv_dir" ]]; then
        log_info "创建 Python 虚拟环境..."
        "$PYTHON_CMD" -m venv "$venv_dir"
    fi
    # shellcheck source=/dev/null
    source "$venv_dir/bin/activate"
    log_info "虚拟环境已激活: $venv_dir"
}

install_deps() {
    log_info "安装 Python 依赖..."
    pip install --quiet --upgrade pip
    pip install --quiet -r "$BACKEND_DIR/requirements.txt"
    log_info "依赖安装完成"
}

start_postgres() {
    if docker ps --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NAME}$"; then
        log_info "PostgreSQL 容器已在运行: $DB_CONTAINER_NAME"
        return 0
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${DB_CONTAINER_NAME}$"; then
        log_info "启动已存在的 PostgreSQL 容器..."
        docker start "$DB_CONTAINER_NAME"
    else
        log_info "创建并启动 PostgreSQL 容器..."
        docker run -d \
            --name "$DB_CONTAINER_NAME" \
            -e POSTGRES_USER="$DB_USER" \
            -e POSTGRES_PASSWORD="$DB_PASSWORD" \
            -e POSTGRES_DB="$DB_NAME" \
            -p "${DB_PORT}:5432" \
            --restart unless-stopped \
            postgres:15-alpine
    fi

    log_info "等待 PostgreSQL 就绪..."
    local retries=30
    while [[ $retries -gt 0 ]]; do
        if docker exec "$DB_CONTAINER_NAME" pg_isready -U "$DB_USER" &> /dev/null; then
            log_info "PostgreSQL 已就绪"
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done

    if [[ $retries -eq 0 ]]; then
        log_error "PostgreSQL 启动超时"
        exit 1
    fi

    # 创建测试数据库（如果不存在）
    docker exec "$DB_CONTAINER_NAME" psql -U "$DB_USER" -tc \
        "SELECT 1 FROM pg_database WHERE datname='$DB_TEST_NAME'" \
        | grep -q 1 || \
        docker exec "$DB_CONTAINER_NAME" psql -U "$DB_USER" \
        -c "CREATE DATABASE $DB_TEST_NAME;" && \
        log_info "测试数据库 $DB_TEST_NAME 已创建"
}

start_redis() {
    if docker ps --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        log_info "Redis 容器已在运行: $REDIS_CONTAINER_NAME"
        return 0
    fi

    if docker ps -a --format '{{.Names}}' | grep -q "^${REDIS_CONTAINER_NAME}$"; then
        log_info "启动已存在的 Redis 容器..."
        docker start "$REDIS_CONTAINER_NAME"
    else
        log_info "创建并启动 Redis 容器..."
        docker run -d \
            --name "$REDIS_CONTAINER_NAME" \
            -p "${REDIS_PORT}:6379" \
            --restart unless-stopped \
            redis:7-alpine
    fi

    log_info "等待 Redis 就绪..."
    local retries=15
    while [[ $retries -gt 0 ]]; do
        if docker exec "$REDIS_CONTAINER_NAME" redis-cli ping &> /dev/null; then
            log_info "Redis 已就绪"
            break
        fi
        retries=$((retries - 1))
        sleep 1
    done

    if [[ $retries -eq 0 ]]; then
        log_error "Redis 启动超时"
        exit 1
    fi
}

setup_env_file() {
    local env_file="$BACKEND_DIR/.env"
    if [[ ! -f "$env_file" ]]; then
        log_info "生成 .env 配置文件..."
        cat > "$env_file" <<EOF
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@localhost:${DB_PORT}/${DB_NAME}
REDIS_URL=redis://localhost:${REDIS_PORT}/0
JWT_SECRET=$(openssl rand -hex 32)
JWT_EXPIRE_MINUTES=480
PROMETHEUS_URL=http://prometheus.idc.internal:9090
EOF
        log_info ".env 文件已生成: $env_file"
    else
        log_info ".env 文件已存在，跳过生成"
    fi
}

run_migration() {
    log_info "执行数据库迁移..."
    cd "$BACKEND_DIR"
    alembic upgrade head
    log_info "数据库迁移完成"
}

start_api() {
    local pid_file="/tmp/inspection-api.pid"
    local log_file="/tmp/inspection-api.log"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "API 服务已在运行 (PID: $(cat "$pid_file"))"
        return 0
    fi

    log_info "启动 API 服务 (端口: $API_PORT)..."
    cd "$BACKEND_DIR"
    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port "$API_PORT" \
        --workers 2 \
        >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
    log_info "API 服务已启动 (PID: $!, 日志: $log_file)"
}

start_worker() {
    local pid_file="/tmp/inspection-worker.pid"
    local log_file="/tmp/inspection-worker.log"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "Celery Worker 已在运行 (PID: $(cat "$pid_file"))"
        return 0
    fi

    log_info "启动 Celery Worker..."
    cd "$BACKEND_DIR"
    nohup celery -A app.tasks.celery_app worker \
        --loglevel=info \
        --concurrency=4 \
        >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
    log_info "Celery Worker 已启动 (PID: $!, 日志: $log_file)"
}

start_beat() {
    local pid_file="/tmp/inspection-beat.pid"
    local log_file="/tmp/inspection-beat.log"

    if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
        log_warn "Celery Beat 已在运行 (PID: $(cat "$pid_file"))"
        return 0
    fi

    log_info "启动 Celery Beat (定时任务调度)..."
    cd "$BACKEND_DIR"
    nohup celery -A app.tasks.celery_app beat \
        --loglevel=info \
        >> "$log_file" 2>&1 &
    echo $! > "$pid_file"
    log_info "Celery Beat 已启动 (PID: $!, 日志: $log_file)"
}

stop_services() {
    log_info "停止所有服务..."
    for name in api worker beat; do
        local pid_file="/tmp/inspection-${name}.pid"
        if [[ -f "$pid_file" ]]; then
            local pid
            pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                kill "$pid"
                log_info "已停止 $name (PID: $pid)"
            fi
            rm -f "$pid_file"
        fi
    done

    docker stop "$DB_CONTAINER_NAME" "$REDIS_CONTAINER_NAME" 2>/dev/null || true
    log_info "所有服务已停止"
}

show_status() {
    echo ""
    echo "========== 服务状态 =========="
    for name in api worker beat; do
        local pid_file="/tmp/inspection-${name}.pid"
        if [[ -f "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
            echo -e "  ${GREEN}●${NC} $name (PID: $(cat "$pid_file"))"
        else
            echo -e "  ${RED}○${NC} $name (未运行)"
        fi
    done

    echo ""
    echo "========== 容器状态 =========="
    for container in "$DB_CONTAINER_NAME" "$REDIS_CONTAINER_NAME"; do
        if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${container}$"; then
            echo -e "  ${GREEN}●${NC} $container (运行中)"
        else
            echo -e "  ${RED}○${NC} $container (未运行)"
        fi
    done
    echo ""
}

show_logs() {
    echo "选择要查看的日志:"
    echo "  1) API"
    echo "  2) Celery Worker"
    echo "  3) Celery Beat"
    read -r -p "请输入选项 [1-3]: " choice
    case "$choice" in
        1) tail -f /tmp/inspection-api.log ;;
        2) tail -f /tmp/inspection-worker.log ;;
        3) tail -f /tmp/inspection-beat.log ;;
        *) log_error "无效选项" ;;
    esac
}

clean_all() {
    log_warn "此操作将删除所有容器和数据，无法恢复！"
    read -r -p "确认清理？输入 'yes' 继续: " confirm
    if [[ "$confirm" != "yes" ]]; then
        log_info "已取消"
        exit 0
    fi

    stop_services
    docker rm -f "$DB_CONTAINER_NAME" "$REDIS_CONTAINER_NAME" 2>/dev/null || true
    rm -f /tmp/inspection-*.pid /tmp/inspection-*.log
    log_info "清理完成"
}

# ========== 主流程 ==========

MODE="full"
SKIP_DEPS=false
SKIP_MIGRATION=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --help)       show_help; exit 0 ;;
        --stop)       MODE="stop" ;;
        --restart)    MODE="restart" ;;
        --status)     MODE="status" ;;
        --logs)       MODE="logs" ;;
        --clean)      MODE="clean" ;;
        --api-only)   MODE="api" ;;
        --worker-only) MODE="worker" ;;
        --beat-only)  MODE="beat" ;;
        --skip-deps)  SKIP_DEPS=true ;;
        --skip-migration) SKIP_MIGRATION=true ;;
        *) log_error "未知选项: $1"; show_help; exit 1 ;;
    esac
    shift
done

case "$MODE" in
    stop)
        stop_services
        exit 0
        ;;
    restart)
        stop_services
        sleep 2
        MODE="full"
        ;;
    status)
        show_status
        exit 0
        ;;
    logs)
        show_logs
        exit 0
        ;;
    clean)
        clean_all
        exit 0
        ;;
esac

# 启动流程
log_info "===== 运维巡检系统启动 ====="
check_os
check_docker
check_python
check_db_password
setup_venv

[[ "$SKIP_DEPS" == false ]] && install_deps

start_postgres
start_redis
setup_env_file

[[ "$SKIP_MIGRATION" == false ]] && run_migration

case "$MODE" in
    full)
        start_api
        start_worker
        start_beat
        ;;
    api)
        start_api
        ;;
    worker)
        start_worker
        ;;
    beat)
        start_beat
        ;;
esac

show_status
log_info "===== 启动完成 ====="
log_info "API 地址: http://localhost:${API_PORT}"
log_info "API 文档: http://localhost:${API_PORT}/docs"
