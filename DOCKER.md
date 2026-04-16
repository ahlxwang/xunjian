# Docker 部署指南

## 系统依赖

### 基础环境
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+ (可选，推荐使用)
- **操作系统**: Linux/macOS/Windows (WSL2)

### 镜像说明
本系统使用以下 Docker 镜像：
- **应用镜像**: `inspection-app:latest` (基于 Python 3.11-slim)
- **PostgreSQL**: `postgres:15-alpine`
- **Redis**: `redis:7-alpine`

### 应用镜像特性
- **多阶段构建**: 分离构建依赖和运行时依赖，减小镜像体积
- **非 root 用户**: 使用 UID 1000 的 appuser 运行，提升安全性
- **健康检查**: 内置 HTTP 健康检查端点
- **优化层缓存**: requirements.txt 单独复制，加速重复构建

## 快速开始

### 方式一：使用 docker-compose（推荐）

1. **准备配置文件**
```bash
cd backend
cp .env.example .env
# 编辑 .env 配置云厂商凭证
```

2. **构建镜像**
```bash
./build-docker.sh
```

3. **启动所有服务**
```bash
docker-compose up -d
```

4. **查看服务状态**
```bash
docker-compose ps
```

5. **查看日志**
```bash
# 所有服务
docker-compose logs -f

# 单个服务
docker-compose logs -f api
docker-compose logs -f worker
```

6. **停止服务**
```bash
docker-compose down
```

### 方式二：使用独立脚本

1. **准备配置文件**（同上）

2. **构建镜像**
```bash
./build-docker.sh
```

3. **启动所有容器**
```bash
./run-docker.sh
```

此脚本会依次启动：
- PostgreSQL 容器
- Redis 容器
- 执行数据库迁移
- API 服务容器
- Celery Worker 容器
- Celery Beat 容器

## 服务架构

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Network                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  PostgreSQL  │  │    Redis     │  │   API (8000) │  │
│  │   (5432)     │  │   (6379)     │  │   uvicorn    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         ▲                 ▲                  │           │
│         │                 │                  │           │
│         └─────────────────┴──────────────────┘           │
│                           │                              │
│         ┌─────────────────┴─────────────────┐            │
│         │                                   │            │
│  ┌──────▼──────┐                   ┌───────▼──────┐     │
│  │Celery Worker│                   │ Celery Beat  │     │
│  │ (4 workers) │                   │  (scheduler) │     │
│  └─────────────┘                   └──────────────┘     │
└─────────────────────────────────────────────────────────┘
```

## 容器说明

### 1. postgres
- **镜像**: postgres:15-alpine
- **端口**: 5432
- **数据卷**: postgres_data
- **健康检查**: pg_isready
- **用途**: 存储巡检任务、风险记录、用户数据

### 2. redis
- **镜像**: redis:7-alpine
- **端口**: 6379
- **数据卷**: redis_data
- **持久化**: AOF (appendonly yes)
- **用途**: Celery 消息队列和结果存储

### 3. migrate
- **类型**: 一次性任务容器
- **命令**: alembic upgrade head
- **依赖**: postgres 健康检查通过
- **用途**: 执行数据库表结构迁移

### 4. api
- **端口**: 8000
- **命令**: uvicorn app.main:app --workers 2
- **依赖**: migrate 完成、postgres/redis 健康
- **用途**: 提供 REST API 和 Swagger 文档

### 5. worker
- **命令**: celery worker --concurrency 4
- **依赖**: migrate 完成、redis 健康
- **用途**: 执行异步巡检任务

### 6. beat
- **命令**: celery beat
- **依赖**: migrate 完成、redis 健康
- **用途**: 定时触发巡检任务（每天凌晨2点）

## 环境变量配置

容器内环境变量通过以下方式设置：

1. **env_file**: 从 `backend/.env` 加载
2. **environment**: docker-compose.yml 中覆盖数据库/Redis 连接串

关键环境变量：
```bash
# 数据库连接（容器内使用服务名）
DATABASE_URL=postgresql+asyncpg://inspector:password@postgres:5432/inspection

# Redis 连接（容器内使用服务名）
REDIS_URL=redis://redis:6379/0

# JWT 密钥（必须修改）
JWT_SECRET=change-me-to-a-random-secret-at-least-32-chars

# 云厂商凭证（根据实际情况配置）
ALIYUN_ACCESS_KEY_ID=your-key
ALIYUN_ACCESS_KEY_SECRET=your-secret
TENCENT_SECRET_ID=your-id
TENCENT_SECRET_KEY=your-key
HUAWEI_ACCESS_KEY=your-key
HUAWEI_SECRET_KEY=your-secret

# K8s 配置模式
K8S_CONFIG_MODE=incluster  # 容器内推荐使用 incluster 模式
```

## 数据持久化

### 数据卷
```yaml
volumes:
  postgres_data:  # PostgreSQL 数据目录
  redis_data:     # Redis AOF 持久化文件
```

### 备份数据
```bash
# 备份 PostgreSQL
docker exec inspection-postgres pg_dump -U inspector inspection > backup.sql

# 备份 Redis
docker exec inspection-redis redis-cli BGSAVE
docker cp inspection-redis:/data/dump.rdb ./redis-backup.rdb
```

### 恢复数据
```bash
# 恢复 PostgreSQL
docker exec -i inspection-postgres psql -U inspector inspection < backup.sql

# 恢复 Redis
docker cp ./redis-backup.rdb inspection-redis:/data/dump.rdb
docker restart inspection-redis
```

## 常用操作

### 查看容器状态
```bash
docker-compose ps
```

### 进入容器 Shell
```bash
# API 容器
docker exec -it inspection-api bash

# PostgreSQL 容器
docker exec -it inspection-postgres psql -U inspector -d inspection
```

### 重启单个服务
```bash
docker-compose restart api
docker-compose restart worker
```

### 查看资源占用
```bash
docker stats
```

### 清理未使用资源
```bash
# 清理停止的容器
docker container prune

# 清理未使用的镜像
docker image prune

# 清理未使用的数据卷
docker volume prune
```

## 生产环境建议

### 1. 安全加固
- 修改默认数据库密码
- 使用 Docker Secrets 管理敏感信息
- 限制容器资源使用（CPU/内存）
- 启用 Docker 内容信任（DCT）

### 2. 资源限制
在 docker-compose.yml 中添加：
```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### 3. 日志管理
配置日志驱动：
```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 4. 健康检查
所有服务已配置健康检查，可通过以下命令验证：
```bash
docker inspect --format='{{.State.Health.Status}}' inspection-api
```

### 5. 监控集成
- 使用 Prometheus 抓取容器指标
- 配置 Grafana 仪表盘
- 设置告警规则

## 故障排查

### 容器无法启动
```bash
# 查看容器日志
docker-compose logs <service-name>

# 查看容器详细信息
docker inspect <container-name>
```

### 数据库连接失败
```bash
# 检查 PostgreSQL 是否就绪
docker exec inspection-postgres pg_isready -U inspector

# 检查网络连通性
docker exec inspection-api ping postgres
```

### Celery 任务不执行
```bash
# 检查 Worker 日志
docker-compose logs worker

# 检查 Redis 连接
docker exec inspection-worker redis-cli -h redis ping

# 查看 Celery 队列
docker exec inspection-worker celery -A app.tasks.celery_app.celery inspect active
```

### 端口冲突
如果 8000/5432/6379 端口被占用，修改 docker-compose.yml：
```yaml
ports:
  - "8001:8000"  # 映射到宿主机 8001 端口
```

## 性能优化

### 1. Worker 并发数调整
根据 CPU 核心数调整：
```yaml
worker:
  command: celery worker --concurrency 8  # 默认 4
```

### 2. API Workers 数量
```yaml
api:
  command: uvicorn app.main:app --workers 4  # 默认 2
```

### 3. PostgreSQL 连接池
在 .env 中配置：
```bash
DATABASE_URL=postgresql+asyncpg://inspector:password@postgres:5432/inspection?pool_size=20&max_overflow=10
```

### 4. Redis 内存限制
```yaml
redis:
  command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

## 更新部署

### 滚动更新
```bash
# 1. 构建新镜像
./build-docker.sh

# 2. 重启服务（零停机）
docker-compose up -d --no-deps --build api
docker-compose up -d --no-deps --build worker
docker-compose up -d --no-deps --build beat
```

### 回滚版本
```bash
# 使用旧镜像标签
docker-compose down
docker tag inspection-app:latest inspection-app:backup
docker tag inspection-app:v1.0 inspection-app:latest
docker-compose up -d
```

## 常见问题

**Q: 如何修改数据库密码？**
A: 修改 docker-compose.yml 中的 POSTGRES_PASSWORD 和 DATABASE_URL，删除数据卷后重新启动。

**Q: 容器重启后数据丢失？**
A: 检查数据卷是否正确挂载，使用 `docker volume ls` 查看。

**Q: 如何扩展 Worker 数量？**
A: 使用 `docker-compose up -d --scale worker=3` 启动 3 个 Worker 实例。

**Q: 如何在 Kubernetes 中部署？**
A: 参考 k8s/ 目录下的 manifests，或使用 Helm Chart（待开发）。
