# 运维巡检系统 - 使用白皮书

**版本**: v1.0  
**更新日期**: 2026-04-16  
**适用范围**: 多云混合环境（阿里云/腾讯云/华为云 + 自建IDC）

---

## 目录

1. [系统概述](#1-系统概述)
2. [快速开始](#2-快速开始)
3. [Docker 部署](#3-docker-部署)
4. [系统架构](#4-系统架构)
5. [功能说明](#5-功能说明)
6. [API 接口文档](#6-api-接口文档)
7. [配置说明](#7-配置说明)
8. [运维指南](#8-运维指南)
9. [常见问题](#9-常见问题)

---

## 1. 系统概述

### 1.1 项目背景

在多云混合环境下，需要对大规模基础设施（50+ 主机、多 K8s 集群、10+ 数据库实例）进行统一的自动化巡检，及时发现潜在风险，提升运维效率。

### 1.2 核心功能

- **统一巡检入口**: 一键触发全平台巡检（阿里云/腾讯云/华为云/IDC/K8s）
- **风险可视化**: 直观展示严重/高风险项，支持按云平台、资源类型、风险等级筛选
- **自动化运行**: 每天 8:00 自动巡检并邮件通知
- **历史追溯**: 保留 30 天巡检记录，支持趋势对比
- **权限管控**: 管理员/运维/开发三级权限，开发人员只能查看负责服务的风险

### 1.3 技术栈

- **后端**: Python 3.11 / FastAPI 0.104 / SQLAlchemy 2.0 / Celery 5.3 / Redis 5.0
- **数据库**: PostgreSQL 15 (异步驱动 asyncpg)
- **前端**: Vue 3 / Element Plus / ECharts (规划中，当前为原型)
- **部署**: Docker / Kubernetes
- **监控数据源**:
  - IDC 机房: Prometheus
  - 阿里云: aliyun-python-sdk-core
  - 腾讯云: tencentcloud-sdk-python
  - 华为云: huaweicloudsdkcore
  - K8s: kubernetes-client

### 1.4 支持的资源类型

| 资源类型 | 采集指标 | 风险规则示例 |
|---------|---------|------------|
| **主机** (Host) | CPU/内存/磁盘使用率 | CPU > 80% (高风险) / > 90% (严重) |
| **容器** (Container) | Pod 状态、重启次数 | CrashLoopBackOff (严重)、重启 > 5 次/小时 (高风险) |
| **数据库** (Database) | 连接数、慢查询、内存 | MySQL 连接数 > 90% (严重)、慢查询 > 100 条/小时 (高风险) |

---

## 2. 快速开始

### 2.1 环境要求

- Python 3.11+
- PostgreSQL 15+
- Redis 6+
- Docker (可选，用于快速拉起依赖)

### 2.2 一键启动（推荐）

```bash
# 1. 克隆项目
cd 巡检

# 2. 配置环境变量（首次运行）
cd backend
cp .env.example .env
# 编辑 .env 填写必要配置（见下方 2.3 节）

# 3. 一键启动所有服务
cd ..
./dev-start.sh
```

**启动脚本功能**:
- 自动安装 Python 依赖
- 检查 `.env` 配置完整性
- 启动 PostgreSQL + Redis (Docker 容器)
- 执行数据库迁移 (`alembic upgrade head`)
- 启动 FastAPI (端口 8000)
- 启动 Celery Worker + Beat (定时任务)
- `Ctrl+C` 自动清理所有进程

**可选参数**:
```bash
./dev-start.sh --skip-deps    # 跳过 pip install（依赖已安装时）
./dev-start.sh --skip-db      # 跳过 Docker 启动（已有外部 PostgreSQL/Redis）
```

### 2.3 环境变量配置

编辑 `backend/.env`，必填项：

```bash
# 数据库（PostgreSQL）
DATABASE_URL=postgresql+asyncpg://inspector:password@localhost:5432/inspection

# Redis（Celery 消息队列 + 缓存）
REDIS_URL=redis://localhost:6379/0

# JWT 认证（至少 32 位随机字符串）
JWT_SECRET=your-super-secret-key-min-32-chars
JWT_EXPIRE_MINUTES=480

# Prometheus（IDC 监控）
PROMETHEUS_URL=http://prometheus.example.com:9090

# 阿里云（可选，不填则跳过阿里云采集）
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_REGION=cn-hangzhou

# 腾讯云（可选）
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
TENCENT_REGION=ap-guangzhou

# 华为云（可选）
HUAWEI_ACCESS_KEY=
HUAWEI_SECRET_KEY=
HUAWEI_REGION=cn-north-4

# Kubernetes（可选）
K8S_CONFIG_MODE=kubeconfig  # 或 incluster（Pod 内运行时）
K8S_KUBECONFIG_PATH=~/.kube/config
```

### 2.4 手动启动（分步）

如果不使用一键脚本，可按以下步骤手动启动：

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 启动 PostgreSQL + Redis（Docker 方式）
docker run -d --name inspection-postgres \
  -e POSTGRES_USER=inspector \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=inspection \
  -p 5432:5432 postgres:15

docker run -d --name inspection-redis \
  -p 6379:6379 redis:7

# 3. 执行数据库迁移
alembic upgrade head

# 4. 启动 API 服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 5. 启动 Celery Worker（新终端）
celery -A app.tasks.celery_app.celery worker -l info

# 6. 启动 Celery Beat（新终端）
celery -A app.tasks.celery_app.celery beat -l info
```

### 2.5 验证启动

访问以下地址确认服务正常：

- **健康检查**: http://127.0.0.1:8000/health  
  返回 `{"status": "ok"}`

- **API 文档**: http://127.0.0.1:8000/docs  
  Swagger UI 交互式文档

---

## 3. Docker 部署

### 3.1 快速部署（推荐）

使用 Docker Compose 一键启动完整系统（包含 PostgreSQL、Redis、API、Worker、Beat）：

```bash
# 1. 构建镜像
./build-docker.sh

# 2. 配置环境变量
cd backend
cp .env.example .env
# 编辑 .env 填写云平台凭证（见 2.3 节）

# 3. 启动所有服务
cd ..
docker-compose up -d

# 4. 查看日志
docker-compose logs -f api

# 5. 验证服务
curl http://localhost:8000/health
```

**服务架构**:
- `postgres`: PostgreSQL 15 数据库（端口 5432）
- `redis`: Redis 7 缓存（端口 6379）
- `migrate`: 数据库迁移（一次性任务）
- `api`: FastAPI 服务（端口 8000，2 workers）
- `worker`: Celery 异步任务处理（4 并发）
- `beat`: Celery 定时任务调度

### 3.2 独立脚本部署

不使用 Docker Compose 时，可用独立脚本启动：

```bash
# 1. 构建镜像
./build-docker.sh

# 2. 配置环境变量（同上）

# 3. 启动所有容器
./run-docker.sh

# 4. 停止所有容器
./run-docker.sh stop
```

### 3.3 常用操作

```bash
# 查看运行状态
docker-compose ps

# 重启 API 服务
docker-compose restart api

# 查看 Worker 日志
docker-compose logs -f worker

# 进入容器调试
docker-compose exec api bash

# 停止所有服务
docker-compose down

# 停止并删除数据卷（危险操作！）
docker-compose down -v
```

### 3.4 生产环境建议

1. **资源限制**: 编辑 `docker-compose.yml` 添加 CPU/内存限制
2. **数据备份**: 定期备份 PostgreSQL 数据卷（`postgres_data`）
3. **日志管理**: 配置日志驱动（如 `json-file` 限制大小）
4. **安全加固**: 修改默认密码、使用 Docker Secrets 管理敏感信息
5. **监控告警**: 集成 Prometheus 监控容器指标

**详细文档**: 参见 [DOCKER.md](./DOCKER.md) 获取完整部署指南、故障排查和性能优化建议。

---

## 4. 系统架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                    Web 前端 (Vue3 - 规划中)                  │
│  巡检概览 | 风险管理 | 历史记录 | 规则配置 | 用户管理        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    API 服务 (FastAPI)                        │
│  认证鉴权 | RESTful API | WebSocket推送 | 任务调度接口      │
└────────────┬───────────────────────────────┬────────────────┘
             │                               │
    ┌────────▼────────┐            ┌────────▼────────┐
    │  PostgreSQL 15  │            │  Redis 6+       │
    │  (数据持久化)    │            │  (缓存+消息队列) │
    └─────────────────┘            └────────┬────────┘
                                            │
                                   ┌────────▼────────┐
                                   │  Celery Worker  │
                                   │  (异步任务执行)  │
                                   └────────┬────────┘
                                            │
        ┌───────────────┬───────────────────┼───────────────┬───────────┐
        │               │                   │               │           │
┌───────▼────────┐ ┌────▼──────────┐ ┌─────▼──────┐ ┌─────▼─────┐ ┌───▼────┐
│ PrometheusCol  │ │ AliyunCol     │ │ TencentCol │ │ HuaweiCol │ │ K8sCol │
│ (IDC监控)      │ │ (阿里云ECS/RDS)│ │ (腾讯云CVM) │ │ (华为云ECS)│ │ (K8s)  │
└────────────────┘ └───────────────┘ └────────────┘ └───────────┘ └────────┘
```

### 3.2 核心模块

#### 3.2.1 采集层 (Collector Layer)

**职责**: 从各数据源获取监控指标

**实现类**:
- `PrometheusCollector`: IDC Prometheus 指标查询
- `AliyunCollector`: 阿里云 ECS/RDS/Redis 监控数据
- `TencentCollector`: 腾讯云 CVM/TencentDB 监控数据
- `HuaweiCollector`: 华为云 ECS/RDS 监控数据
- `K8sCollector`: K8s API 获取 Pod/Node 状态

**统一接口** (`BaseCollector`):
```python
class BaseCollector(ABC):
    @abstractmethod
    async def collect_hosts(self) -> list[HostMetric]:
        """采集主机指标"""
        
    @abstractmethod
    async def collect_databases(self) -> list[DBMetric]:
        """采集数据库指标"""
        
    @abstractmethod
    async def collect_containers(self) -> list[ContainerMetric]:
        """采集容器指标"""
```

**容错机制**:
- 单个采集器失败不影响其他采集器
- 使用 `asyncio.gather(..., return_exceptions=True)` 并发执行
- 异常日志不包含敏感信息（仅记录异常类型）

#### 3.2.2 规则引擎 (Rule Engine)

**职责**: 根据预设规则判断风险等级

**预设规则** (存储在 `rules` 表):

| 规则代码 | 资源类型 | 指标 | 阈值 | 风险等级 |
|---------|---------|------|------|---------|
| `host_cpu_high` | host | cpu_usage_percent | > 80 | high |
| `host_cpu_critical` | host | cpu_usage_percent | > 90 | critical |
| `host_memory_high` | host | memory_usage_percent | > 85 | high |
| `host_disk_critical` | host | disk_usage_percent | > 95 | critical |
| `container_crash` | container | pod_status | == CrashLoopBackOff | critical |
| `db_conn_critical` | database | connection_usage_percent | > 90 | critical |

**规则配置**: 支持 Web 界面动态调整阈值（`PATCH /api/v1/rules/{id}`）

#### 3.2.3 调度层 (Scheduler)

**Celery Beat 定时任务**:
- 每天 8:00 触发全量巡检
- 每天 2:00 清理 30 天前的历史数据

**手动触发**: `POST /api/v1/inspection/trigger`

#### 3.2.4 API 层 (FastAPI)

**认证**: JWT Token (Bearer)

**权限模型** (RBAC):
- `admin`: 全部权限
- `ops`: 查看巡检结果 + 标记风险状态 + 调整规则阈值
- `dev`: 只读自己负责服务的巡检结果

---

## 4. 功能说明

### 4.1 巡检流程

```
1. 触发巡检 (手动/定时)
   ↓
2. 创建 InspectionTask 记录 (status=running)
   ↓
3. 并发执行 5 个采集器 (Prometheus/Aliyun/Tencent/Huawei/K8s)
   ↓
4. 聚合所有指标数据 (hosts/databases/containers)
   ↓
5. 规则引擎评估风险 (遍历所有规则，匹配阈值)
   ↓
6. 生成 RiskItem 记录 (risk_level: critical/high/medium/low)
   ↓
7. 更新 InspectionTask (status=completed, risk_count)
   ↓
8. 发送邮件通知 (严重风险摘要)
```

### 4.2 风险管理

**风险状态流转**:
```
pending (待处理) → processing (处理中) → resolved (已解决)
                                      ↘ ignored (已忽略)
```

**操作权限**:
- `admin/ops`: 可更新所有风险项状态
- `dev`: 只能更新自己负责服务的风险项

### 4.3 数据清理

**清理策略**:
- 每天凌晨 2:00 运行 Celery 定期任务
- 将 30 天前的 `risk_items` 归档到 `risk_items_archive` 表
- 删除 30 天前的 `inspection_tasks` 记录

**归档表**: 只保留用于趋势分析的必要字段，不做实时查询

---

## 5. API 接口文档

### 5.1 认证接口

#### POST /api/v1/auth/login

**请求体**:
```json
{
  "username": "admin",
  "password": "password"
}
```

**响应**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "role": "admin"
}
```

**使用方式**: 后续请求在 Header 中携带 `Authorization: Bearer <token>`

---

### 5.2 巡检接口

#### POST /api/v1/inspection/trigger

**权限**: `admin` / `ops`

**响应**:
```json
{
  "task_id": "abc123-def456",
  "status": "running"
}
```

---

#### GET /api/v1/inspection/latest

**权限**: 所有登录用户

**响应**:
```json
{
  "task": {
    "id": 1,
    "task_id": "abc123-def456",
    "status": "completed",
    "trigger_type": "manual",
    "start_time": "2026-04-16T08:00:00",
    "end_time": "2026-04-16T08:05:23",
    "total_resources": 128,
    "risk_count": {
      "critical": 3,
      "high": 12,
      "medium": 28,
      "low": 5
    },
    "created_at": "2026-04-16T08:00:00"
  }
}
```

---

#### GET /api/v1/inspection/history

**权限**: 所有登录用户

**查询参数**:
- `limit`: 返回记录数 (默认 30)

**响应**: 巡检任务列表 (同上 `task` 结构)

---

### 5.3 风险接口

#### GET /api/v1/risks

**权限**: 所有登录用户 (`dev` 角色只能看自己负责的服务)

**查询参数**:
- `risk_level`: 风险等级 (critical/high/medium/low)
- `status`: 状态 (pending/processing/ignored/resolved)
- `cloud_provider`: 云平台 (aliyun/tencent/huawei/idc)
- `resource_type`: 资源类型 (host/container/database)
- `page`: 页码 (默认 1)
- `page_size`: 每页数量 (默认 20，最大 100)

**响应**:
```json
{
  "items": [
    {
      "id": 1,
      "inspection_id": 1,
      "resource_type": "host",
      "resource_id": "i-abc123",
      "resource_name": "web-server-01",
      "cloud_provider": "aliyun",
      "region": "cn-hangzhou",
      "rule_id": 1,
      "risk_level": "critical",
      "risk_title": "主机 CPU 使用率过高",
      "risk_detail": "当前 CPU 使用率 95.2%，超过阈值 90%",
      "metric_value": 95.2,
      "threshold_value": 90.0,
      "status": "pending",
      "assigned_to": null,
      "resolved_at": null,
      "created_at": "2026-04-16T08:05:00"
    }
  ],
  "total": 48
}
```

---

#### PATCH /api/v1/risks/{risk_id}/status

**权限**: 所有登录用户 (`dev` 角色只能更新自己负责的服务)

**请求体**:
```json
{
  "status": "resolved"
}
```

**响应**: 更新后的风险项 (同上 `items[0]` 结构)

---

### 5.4 规则接口

#### GET /api/v1/rules

**权限**: 所有登录用户

**响应**:
```json
[
  {
    "id": 1,
    "rule_code": "host_cpu_critical",
    "rule_name": "主机 CPU 使用率严重",
    "resource_type": "host",
    "metric_name": "cpu_usage_percent",
    "operator": ">",
    "threshold_value": 90.0,
    "risk_level": "critical",
    "enabled": true,
    "description": "CPU 使用率超过 90% 视为严重风险",
    "created_at": "2026-04-15T10:00:00"
  }
]
```

---

#### PATCH /api/v1/rules/{rule_id}

**权限**: `admin` / `ops`

**请求体**:
```json
{
  "threshold_value": 85.0,
  "enabled": true
}
```

**响应**: 更新后的规则 (同上结构)

---

## 6. 配置说明

### 6.1 环境变量详解

| 变量名 | 必填 | 默认值 | 说明 |
|-------|------|--------|------|
| `DATABASE_URL` | ✅ | - | PostgreSQL 连接串 (格式: `postgresql+asyncpg://user:pass@host:port/db`) |
| `REDIS_URL` | ✅ | - | Redis 连接串 (格式: `redis://host:port/db`) |
| `JWT_SECRET` | ✅ | - | JWT 签名密钥 (至少 32 位) |
| `JWT_EXPIRE_MINUTES` | ❌ | 480 | Token 过期时间 (分钟) |
| `PROMETHEUS_URL` | ✅ | - | IDC Prometheus 地址 |
| `ALIYUN_ACCESS_KEY_ID` | ❌ | None | 阿里云 AccessKey ID (不填则跳过阿里云采集) |
| `ALIYUN_ACCESS_KEY_SECRET` | ❌ | None | 阿里云 AccessKey Secret |
| `ALIYUN_REGION` | ❌ | cn-hangzhou | 阿里云区域 |
| `TENCENT_SECRET_ID` | ❌ | None | 腾讯云 SecretId |
| `TENCENT_SECRET_KEY` | ❌ | None | 腾讯云 SecretKey |
| `TENCENT_REGION` | ❌ | ap-guangzhou | 腾讯云区域 |
| `HUAWEI_ACCESS_KEY` | ❌ | None | 华为云 AccessKey |
| `HUAWEI_SECRET_KEY` | ❌ | None | 华为云 SecretKey |
| `HUAWEI_REGION` | ❌ | cn-north-4 | 华为云区域 |
| `K8S_CONFIG_MODE` | ❌ | kubeconfig | K8s 配置模式 (`kubeconfig` 或 `incluster`) |
| `K8S_KUBECONFIG_PATH` | ❌ | None | kubeconfig 文件路径 (mode=kubeconfig 时必填) |

### 6.2 数据库迁移

**查看当前版本**:
```bash
cd backend
alembic current
```

**升级到最新版本**:
```bash
alembic upgrade head
```

**回滚到上一版本**:
```bash
alembic downgrade -1
```

**创建新迁移** (修改 ORM 模型后):
```bash
alembic revision --autogenerate -m "描述"
```

### 6.3 Celery 配置

**定时任务配置** (`backend/app/tasks/celery_app.py`):
```python
celery.conf.beat_schedule = {
    "daily-inspection": {
        "task": "app.tasks.inspection_task.run_inspection",
        "schedule": crontab(hour=8, minute=0),  # 每天 8:00
    },
    "cleanup-old-data": {
        "task": "app.tasks.cleanup_task.cleanup_old_inspections",
        "schedule": crontab(hour=2, minute=0),  # 每天 2:00
    },
}
```

**修改定时任务时间**: 编辑上述文件后重启 Celery Beat

---

## 7. 运维指南

### 7.1 日志查看

**API 日志**:
```bash
# 实时查看
tail -f /var/log/inspection-api.log

# 或直接查看 uvicorn 输出
```

**Celery Worker 日志**:
```bash
tail -f /tmp/celery-worker.log
```

**Celery Beat 日志**:
```bash
tail -f /tmp/celery-beat.log
```

### 7.2 健康检查

**API 健康检查**:
```bash
curl http://127.0.0.1:8000/health
# 预期: {"status": "ok"}
```

**数据库连接检查**:
```bash
psql -h localhost -U inspector -d inspection -c "SELECT 1;"
```

**Redis 连接检查**:
```bash
redis-cli ping
# 预期: PONG
```

### 7.3 性能监控

**Celery 任务队列长度**:
```bash
redis-cli llen celery
```

**数据库连接数**:
```sql
SELECT count(*) FROM pg_stat_activity WHERE datname = 'inspection';
```

**慢查询日志** (PostgreSQL):
```sql
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

### 7.4 备份与恢复

**数据库备份**:
```bash
pg_dump -h localhost -U inspector inspection > backup_$(date +%Y%m%d).sql
```

**数据库恢复**:
```bash
psql -h localhost -U inspector inspection < backup_20260416.sql
```

### 7.5 扩容建议

**水平扩展 Celery Worker**:
```bash
# 启动多个 Worker 实例
celery -A app.tasks.celery_app.celery worker -l info -n worker1@%h &
celery -A app.tasks.celery_app.celery worker -l info -n worker2@%h &
```

**API 服务负载均衡**:
- 使用 Nginx/HAProxy 反向代理多个 uvicorn 实例
- 或使用 Kubernetes Deployment + Service

---

## 8. 常见问题

### 8.1 启动问题

**Q: `python3: command not found`**  
A: 安装 Python 3.11+ 或使用虚拟环境

**Q: `alembic: command not found`**  
A: 确认已执行 `pip install -r requirements.txt`

**Q: 数据库连接失败**  
A: 检查 PostgreSQL 是否启动，`.env` 中 `DATABASE_URL` 是否正确

**Q: Redis 连接失败**  
A: 检查 Redis 是否启动，`.env` 中 `REDIS_URL` 是否正确

### 8.2 采集问题

**Q: 阿里云采集器返回空数据**  
A: 检查 `ALIYUN_ACCESS_KEY_ID` / `ALIYUN_ACCESS_KEY_SECRET` 是否正确，账号是否有 ECS/CMS 权限

**Q: K8s 采集器报错 `Unauthorized`**  
A: 检查 `K8S_KUBECONFIG_PATH` 是否正确，kubeconfig 是否有集群访问权限

**Q: Prometheus 采集器超时**  
A: 检查 `PROMETHEUS_URL` 是否可访问，网络是否通畅

### 8.3 权限问题

**Q: 开发人员看不到风险项**  
A: 确认用户的 `responsible_services` 字段包含对应的服务名称

**Q: 运维人员无法调整规则阈值**  
A: 确认用户角色为 `ops` 或 `admin`

### 8.4 性能问题

**Q: 巡检任务执行时间过长**  
A: 
- 检查各云平台 API 响应时间
- 增加 Celery Worker 数量
- 优化规则数量（禁用不必要的规则）

**Q: 数据库查询慢**  
A:
- 检查索引是否存在 (`risk_items` 表的 `inspection_id`, `status`, `risk_level`, `created_at`)
- 定期执行 `VACUUM ANALYZE`
- 考虑分区表（按月分区 `risk_items`）

---

## 附录

### A. 数据库表结构

详见设计文档: `docs/superpowers/specs/2026-04-15-ops-inspection-system-design.md`

### B. 开发指南

**运行测试**:
```bash
cd backend
pytest tests/ -v
```

**代码覆盖率**:
```bash
pytest tests/ --cov=app --cov-report=html
```

**代码风格检查**:
```bash
flake8 app/ --max-line-length=120
```

### C. 联系方式

- **技术支持**: ops-team@example.com
- **问题反馈**: https://github.com/your-org/inspection-system/issues

---

**文档结束**
