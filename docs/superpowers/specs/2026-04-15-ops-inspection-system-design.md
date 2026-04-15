# 运维巡检系统设计文档

**文档版本**: v1.0  
**创建日期**: 2026-04-15  
**作者**: Claude  
**状态**: 待审核

---

## 1. 项目概述

### 1.1 项目背景
在多云混合环境下（阿里云、腾讯云、华为云 + 自建IDC），需要对大规模基础设施（50+主机、多K8s集群、10+数据库实例）进行统一的自动化巡检，及时发现潜在风险，提升运维效率。

### 1.2 核心目标
- 统一巡检入口：一键触发全平台巡检
- 风险可视化：直观展示严重/高风险项
- 自动化运行：每天8点自动巡检并邮件通知
- 历史追溯：保留30天巡检记录，支持趋势对比
- 权限管控：管理员/运维/开发三级权限

### 1.3 技术选型
- **后端**: Python 3.10+ / FastAPI / Celery / Redis / PostgreSQL
- **前端**: Vue 3 / Element Plus / ECharts
- **部署**: Docker Compose / Kubernetes
- **监控数据源**: 
  - IDC机房: Prometheus (自建)
  - 云平台: 阿里云/腾讯云/华为云 SDK

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                         Web 前端 (Vue3)                      │
│  巡检概览 | 风险管理 | 历史记录 | 规则配置 | 用户管理        │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP/WebSocket
┌────────────────────────▼────────────────────────────────────┐
│                    API 服务 (FastAPI)                        │
│  认证鉴权 | RESTful API | WebSocket推送 | 任务调度接口      │
└────────────┬───────────────────────────────┬────────────────┘
             │                               │
    ┌────────▼────────┐            ┌────────▼────────┐
    │  PostgreSQL     │            │  Redis          │
    │  (数据持久化)    │            │  (缓存+消息队列) │
    └─────────────────┘            └────────┬────────┘
                                            │
                                   ┌────────▼────────┐
                                   │  Celery Worker  │
                                   │  (异步任务执行)  │
                                   └────────┬────────┘
                                            │
        ┌───────────────────────────────────┼───────────────────┐
        │                                   │                   │
┌───────▼────────┐  ┌──────────▼──────────┐  ┌────────▼───────┐
│ 阿里云采集器    │  │ 腾讯云采集器         │  │ 华为云采集器    │
│ (aliyun-sdk)   │  │ (tencentcloud-sdk)  │  │ (huaweicloud)  │
└────────────────┘  └─────────────────────┘  └────────────────┘
                            │
                    ┌───────▼────────┐
                    │ IDC采集器       │
                    │ (Prometheus)   │
                    └────────────────┘
```

### 2.2 模块划分

#### 2.2.1 采集层 (Collector Layer)
- **职责**: 从各数据源获取监控指标
- **组件**:
  - `AliyunCollector`: 阿里云 ECS/RDS/Redis 监控数据
  - `TencentCollector`: 腾讯云 CVM/TencentDB 监控数据
  - `HuaweiCollector`: 华为云 ECS/RDS 监控数据
  - `PrometheusCollector`: IDC Prometheus 指标查询
  - `K8sCollector`: K8s API 获取 Pod/Node 状态
- **接口设计**:
```python
class BaseCollector(ABC):
    @abstractmethod
    async def collect_hosts(self) -> List[HostMetric]:
        """采集主机指标"""
        
    @abstractmethod
    async def collect_databases(self) -> List[DBMetric]:
        """采集数据库指标"""
        
    @abstractmethod
    async def collect_containers(self) -> List[ContainerMetric]:
        """采集容器指标"""
```

#### 2.2.2 规则引擎 (Rule Engine)
- **职责**: 根据预设规则判断风险等级
- **预设规则**:
  - **主机类**:
    - CPU使用率 > 80% (高风险) / > 90% (严重)
    - 内存使用率 > 85% (高风险) / > 95% (严重)
    - 磁盘使用率 > 85% (高风险) / > 95% (严重)
    - 系统负载 > CPU核心数*2 (高风险)
  - **容器类**:
    - Pod CrashLoopBackOff (严重)
    - Pod重启次数 > 5次/小时 (高风险)
    - Node NotReady (严重)
    - 容器CPU/内存超限 (高风险)
  - **数据库类**:
    - MySQL连接数 > 最大连接数*90% (严重)
    - MySQL慢查询 > 100条/小时 (高风险)
    - Redis内存使用率 > 90% (严重)
    - Redis缓存命中率 < 50% (高风险)
    - MongoDB副本集不健康 (严重)
- **规则配置**: 支持Web界面动态调整阈值

#### 2.2.3 调度层 (Scheduler)
- **Celery Beat**: 定时任务调度
  - 每天8:00触发全量巡检
  - 巡检完成后发送邮件汇总
- **手动触发**: API接口支持立即执行巡检
- **任务队列**: Redis作为Broker，支持任务优先级

#### 2.2.4 通知层 (Notification)
- **邮件通知**:
  - 收件人: 可配置（管理员/运维组）
  - 内容: 巡检摘要 + 严重风险列表 + 详情链接
  - 模板: HTML格式，带颜色标识
- **扩展性**: 预留接口支持钉钉/企业微信/Slack

#### 2.2.5 API层 (FastAPI)
- **认证**: JWT Token
- **权限**: RBAC (Role-Based Access Control)
  - `admin`: 全部权限
  - `ops`: 查看巡检结果 + 标记风险状态 + 调整规则阈值
  - `dev`: 只读自己负责服务的巡检结果
- **核心接口**:
  - `POST /api/v1/inspection/trigger`: 手动触发巡检
  - `GET /api/v1/inspection/latest`: 获取最新巡检结果
  - `GET /api/v1/inspection/history`: 巡检历史列表
  - `GET /api/v1/risks`: 风险项列表（支持过滤/分页）
  - `PATCH /api/v1/risks/{id}/status`: 更新风险状态
  - `GET /api/v1/rules`: 规则列表
  - `PATCH /api/v1/rules/{id}`: 更新规则阈值

#### 2.2.6 前端 (Vue3)
- **页面结构**:
  - 巡检概览: 统计卡片 + 风险列表 + 资源分布
  - 风险管理: 风险项详情 + 状态标记 + 历史记录
  - 巡检历史: 时间轴展示 + 趋势对比
  - 规则配置: 规则列表 + 阈值调整
  - 告警设置: 邮件配置 + 通知规则
  - 用户管理: 用户列表 + 角色分配

---

## 3. 数据模型

### 3.1 核心表结构

#### 3.1.1 巡检任务表 (inspection_tasks)
```sql
CREATE TABLE inspection_tasks (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(64) UNIQUE NOT NULL,  -- Celery任务ID
    status VARCHAR(20) NOT NULL,          -- pending/running/completed/failed
    trigger_type VARCHAR(20) NOT NULL,    -- manual/scheduled
    trigger_user_id INT,                  -- 触发用户ID（手动触发时）
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    total_resources INT DEFAULT 0,        -- 巡检资源总数
    risk_count JSONB,                     -- {"critical": 12, "high": 28, "medium": 45, "low": 10}
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.1.2 风险项表 (risk_items)
```sql
CREATE TABLE risk_items (
    id SERIAL PRIMARY KEY,
    inspection_id INT REFERENCES inspection_tasks(id),
    resource_type VARCHAR(20) NOT NULL,   -- host/container/database
    resource_id VARCHAR(128) NOT NULL,    -- 资源唯一标识
    resource_name VARCHAR(256) NOT NULL,  -- 资源名称
    cloud_provider VARCHAR(20),           -- aliyun/tencent/huawei/idc
    region VARCHAR(64),                   -- 区域
    rule_id INT REFERENCES rules(id),
    risk_level VARCHAR(20) NOT NULL,      -- critical/high/medium/low
    risk_title VARCHAR(512) NOT NULL,
    risk_detail TEXT,
    metric_value FLOAT,                   -- 当前指标值
    threshold_value FLOAT,                -- 阈值
    status VARCHAR(20) DEFAULT 'pending', -- pending/processing/ignored/resolved
    assigned_to INT,                      -- 分配给谁处理
    resolved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_risk_inspection ON risk_items(inspection_id);
CREATE INDEX idx_risk_status ON risk_items(status);
CREATE INDEX idx_risk_level ON risk_items(risk_level);
CREATE INDEX idx_risk_created ON risk_items(created_at);  -- 支持按时间范围清理
```

**清理策略**：每天凌晨2点运行 Celery 定期任务，将30天前的 `risk_items` 归档到 `risk_items_archive` 表（结构相同），再从主表删除。归档表只保留用于趋势分析的必要字段，不做实时查询。`inspection_tasks` 同步清理30天前的记录。

#### 3.1.3 规则表 (rules)
```sql
CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    rule_code VARCHAR(64) UNIQUE NOT NULL,  -- host_cpu_high
    rule_name VARCHAR(256) NOT NULL,
    resource_type VARCHAR(20) NOT NULL,
    metric_name VARCHAR(64) NOT NULL,       -- cpu_usage_percent
    operator VARCHAR(10) NOT NULL,          -- >, <, ==, !=
    threshold_value FLOAT NOT NULL,
    risk_level VARCHAR(20) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### 3.1.4 用户表 (users)
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    password_hash VARCHAR(256) NOT NULL,
    email VARCHAR(128),
    role VARCHAR(20) NOT NULL,              -- admin/ops/dev
    responsible_services JSONB,             -- dev角色负责的服务列表
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX idx_user_services ON users USING GIN(responsible_services);  -- 支持 JSONB 包含查询
```

#### 3.1.5 通知配置表 (notification_configs)
```sql
CREATE TABLE notification_configs (
    id SERIAL PRIMARY KEY,
    config_type VARCHAR(20) NOT NULL,       -- email/dingtalk/wechat
    config_data JSONB NOT NULL,             -- {"smtp_host": "...", "recipients": [...]}
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. 核心流程

### 4.1 巡检执行流程

```
1. 触发巡检 (手动/定时)
   ↓
2. 创建巡检任务记录 (inspection_tasks)
   ↓
3. Celery异步执行
   ├─ 并发调用各采集器
   │  ├─ AliyunCollector.collect_all()
   │  ├─ TencentCollector.collect_all()
   │  ├─ HuaweiCollector.collect_all()
   │  └─ PrometheusCollector.collect_all()
   ↓
4. 规则引擎分析
   ├─ 遍历所有指标
   ├─ 匹配规则
   └─ 生成风险项 (risk_items)
   ↓
5. 更新任务状态 (completed)
   ↓
6. 发送通知 (邮件)
   ↓
7. WebSocket推送前端刷新
```

### 4.2 风险处理流程

```
1. 运维人员查看风险列表
   ↓
2. 点击风险项查看详情
   ↓
3. 标记状态
   ├─ "处理中": 分配给自己，开始处理
   ├─ "已忽略": 误报或可接受风险
   └─ "已解决": 问题已修复
   ↓
4. 下次巡检验证
   ├─ 如果指标恢复正常 → 自动标记"已解决"
   └─ 如果仍超阈值 → 创建新风险项
```

---

## 5. 安全设计

### 5.1 密钥管理
- 云平台 AccessKey/SecretKey 存储在环境变量或 Vault
- 数据库密码使用环境变量
- JWT Secret 随机生成，定期轮换

### 5.2 API安全
- 所有API需JWT认证
- 敏感操作（修改规则/删除用户）需admin权限
- 接口限流：同一用户 100次/分钟

### 5.3 数据安全
- 密码使用 bcrypt 加密存储
- 日志脱敏：不打印 AccessKey/密码
- HTTPS传输（生产环境）

---

## 6. 部署方案

### 6.1 Docker Compose (开发/测试)

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: inspection
      POSTGRES_USER: inspector
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data

  api:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    environment:
      DATABASE_URL: postgresql://inspector:${DB_PASSWORD}@postgres/inspection
      REDIS_URL: redis://redis:6379/0
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: .
    command: celery -A app.tasks worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql://inspector:${DB_PASSWORD}@postgres/inspection
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery-beat:
    build: .
    command: celery -A app.tasks beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://inspector:${DB_PASSWORD}@postgres/inspection
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - api

volumes:
  pgdata:
  redisdata:
```

### 6.2 Kubernetes (生产)

```yaml
# 核心组件
- Deployment: api (3副本)
- Deployment: celery-worker (5副本，可HPA)
- Deployment: celery-beat (1副本)
- StatefulSet: postgres (主从)
- StatefulSet: redis (哨兵模式)
- Ingress: HTTPS + 域名

# 配置管理
- ConfigMap: 应用配置
- Secret: 数据库密码/云平台密钥
```

---

## 7. 监控与运维

### 7.1 系统监控
- API性能: Prometheus + Grafana
- Celery任务: Flower监控面板
- 数据库: pg_stat_statements
- 日志: ELK Stack

### 7.2 告警规则
- API响应时间 > 2s
- Celery任务失败率 > 5%
- 数据库连接数 > 80%
- Redis内存使用 > 80%

---

## 8. 扩展性设计

### 8.1 新增云平台
- 实现 `BaseCollector` 接口
- 注册到采集器工厂
- 配置云平台凭证

### 8.2 新增巡检规则
- Web界面添加规则
- 支持自定义表达式（未来）

### 8.3 新增通知渠道
- 实现 `BaseNotifier` 接口
- 配置通知参数

---

## 9. 项目里程碑

### Phase 1: MVP (2周)
- [ ] 基础架构搭建
- [ ] IDC Prometheus采集器
- [ ] 核心规则引擎
- [ ] 基础Web界面
- [ ] 手动触发巡检

### Phase 2: 多云支持 (2周)
- [ ] 阿里云/腾讯云/华为云采集器
- [ ] 定时任务调度
- [ ] 邮件通知
- [ ] 风险状态管理

### Phase 3: 完善功能 (1周)
- [ ] 用户权限系统
- [ ] 巡检历史查询
- [ ] 规则配置界面
- [ ] 部署文档

### Phase 4: 优化上线 (1周)
- [ ] 性能优化
- [ ] 单元测试 (覆盖率>80%)
- [ ] K8s部署配置
- [ ] 生产环境上线

---

## 10. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 云平台API限流 | 采集失败 | 实现指数退避重试 + 缓存机制 |
| 大规模并发巡检超时 | 任务失败 | Celery任务超时设置 + 分批执行 |
| 数据库性能瓶颈 | 查询慢 | 索引优化 + 读写分离 |
| 前端加载慢 | 用户体验差 | 懒加载 + 虚拟滚动 |

---

## 11. 附录

### 11.1 技术栈版本
- Python: 3.10+
- FastAPI: 0.104+
- Celery: 5.3+
- PostgreSQL: 15+
- Redis: 7+
- Vue: 3.3+
- Element Plus: 2.4+

### 11.2 第三方SDK
- aliyun-python-sdk-core
- tencentcloud-sdk-python
- huaweicloudsdkcore
- prometheus-api-client
- kubernetes (Python client)

### 11.3 参考资料
- [FastAPI官方文档](https://fastapi.tiangolo.com/)
- [Celery官方文档](https://docs.celeryq.dev/)
- [阿里云SDK文档](https://help.aliyun.com/document_detail/53090.html)
- [Prometheus查询语法](https://prometheus.io/docs/prometheus/latest/querying/basics/)
