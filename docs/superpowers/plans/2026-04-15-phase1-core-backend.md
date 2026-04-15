# 运维巡检系统 Phase 1：核心后端 MVP 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建运维巡检系统的核心后端，包含数据库模型、JWT认证API、Prometheus采集器、规则引擎和基础巡检流程，能够对 IDC Prometheus 数据执行一次完整的主机巡检并将风险项写入数据库。

**Architecture:** FastAPI 作为 API 层，SQLAlchemy 2.0 (async) 管理 PostgreSQL，Celery + Redis 处理异步巡检任务，采集器通过 BaseCollector 抽象接口统一管理，规则引擎从数据库读取规则动态匹配。

**Tech Stack:** Python 3.10+, FastAPI 0.104+, SQLAlchemy 2.0, Alembic, Celery 5.3+, Redis 7, PostgreSQL 15, pytest, httpx, pytest-asyncio

---

## 文件结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI 入口，注册路由
│   ├── config.py                  # 配置（从环境变量读取）
│   ├── database.py                # SQLAlchemy async engine + session
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py                # User ORM 模型
│   │   ├── inspection.py          # InspectionTask ORM 模型
│   │   ├── risk.py                # RiskItem + RiskItemArchive ORM 模型
│   │   └── rule.py                # Rule ORM 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py                # LoginRequest, TokenResponse
│   │   ├── inspection.py          # InspectionResponse, InspectionHistoryResponse
│   │   ├── risk.py                # RiskItemResponse, RiskStatusUpdate
│   │   └── rule.py                # RuleResponse, RuleUpdate
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py                # 依赖注入：get_db, get_current_user, require_role
│   │   ├── auth.py                # POST /api/v1/auth/login, /logout
│   │   ├── inspection.py          # POST /trigger, GET /latest, GET /history
│   │   ├── risks.py               # GET /risks, PATCH /risks/{id}/status
│   │   └── rules.py               # GET /rules, PATCH /rules/{id}
│   ├── collectors/
│   │   ├── __init__.py
│   │   ├── base.py                # BaseCollector ABC + 数据类型定义
│   │   └── prometheus.py          # PrometheusCollector 实现
│   ├── engine/
│   │   ├── __init__.py
│   │   └── rule_engine.py         # RuleEngine：加载规则、匹配指标、生成风险项
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── celery_app.py          # Celery 实例配置
│   │   ├── inspection_task.py     # run_inspection Celery task
│   │   └── cleanup_task.py        # archive_old_risks Celery task（凌晨2点）
│   └── services/
│       ├── __init__.py
│       └── auth.py                # 密码哈希、JWT 生成/验证
├── migrations/
│   ├── env.py
│   └── versions/
│       └── 0001_initial_schema.py
├── tests/
│   ├── conftest.py                # pytest fixtures：test db, test client, mock data
│   ├── test_auth.py
│   ├── test_inspection_api.py
│   ├── test_risks_api.py
│   ├── test_rule_engine.py
│   └── test_prometheus_collector.py
├── alembic.ini
├── requirements.txt
├── .env.example
└── Dockerfile
```

---

## Task 1: 项目脚手架与依赖配置

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/app/config.py`
- Create: `backend/app/__init__.py`

- [ ] **Step 1: 创建 requirements.txt**

```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy[asyncio]==2.0.23
asyncpg==0.29.0
alembic==1.12.1
celery[redis]==5.3.6
redis==5.0.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
httpx==0.25.2
prometheus-api-client==0.5.3
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-mock==3.12.0
anyio==4.1.0
```

- [ ] **Step 2: 创建 .env.example**

```
DATABASE_URL=postgresql+asyncpg://inspector:password@localhost:5432/inspection
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-to-a-random-secret-at-least-32-chars
JWT_EXPIRE_MINUTES=480

# IDC Prometheus
PROMETHEUS_URL=http://prometheus.idc.internal:9090

# 云平台（Phase 2 使用，Phase 1 留空）
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
HUAWEI_AK=
HUAWEI_SK=
```

- [ ] **Step 3: 创建 app/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 480
    prometheus_url: str = "http://localhost:9090"

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 4: 创建空的 app/__init__.py**

```python
```

- [ ] **Step 5: 安装依赖**

```bash
cd backend
pip install -r requirements.txt
```

期望输出：所有包安装成功，无报错。

- [ ] **Step 6: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app/config.py backend/app/__init__.py
git commit -m "feat: init backend project scaffold"
```

---

## Task 2: 数据库模型与迁移

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/inspection.py`
- Create: `backend/app/models/risk.py`
- Create: `backend/app/models/rule.py`
- Create: `backend/alembic.ini`
- Create: `backend/migrations/env.py`
- Create: `backend/migrations/versions/0001_initial_schema.py`

- [ ] **Step 1: 写失败测试：验证数据库模型字段**

新建 `backend/tests/conftest.py`:

```python
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models import Base

TEST_DB_URL = "postgresql+asyncpg://inspector:password@localhost:5432/inspection_test"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@pytest_asyncio.fixture
async def db(engine):
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()
```

新建 `backend/tests/test_models.py`:

```python
import pytest
from sqlalchemy import select
from app.models.user import User
from app.models.rule import Rule
from app.models.inspection import InspectionTask
from app.models.risk import RiskItem


@pytest.mark.asyncio
async def test_user_model_fields(db):
    user = User(
        username="testuser",
        password_hash="hashed",
        email="test@example.com",
        role="ops",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    assert user.id is not None
    assert user.is_active is True
    assert user.responsible_services is None


@pytest.mark.asyncio
async def test_rule_model_fields(db):
    rule = Rule(
        rule_code="host_cpu_critical",
        rule_name="CPU使用率严重",
        resource_type="host",
        metric_name="cpu_usage_percent",
        operator=">",
        threshold_value=90.0,
        risk_level="critical",
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    assert rule.id is not None
    assert rule.enabled is True
```

- [ ] **Step 2: 运行测试确认失败**

```bash
cd backend
pytest tests/test_models.py -v
```

期望输出：`ImportError` 或 `ModuleNotFoundError`（模型尚未创建）

- [ ] **Step 3: 创建 app/database.py**

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
```

- [ ] **Step 4: 创建 app/models/user.py**

```python
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # admin/ops/dev
    responsible_services: Mapped[dict | None] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 5: 创建 app/models/rule.py**

```python
from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # host/container/database
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)  # >, <, ==, !=
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # critical/high/medium/low
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
```

- [ ] **Step 6: 创建 app/models/inspection.py**

```python
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending/running/completed/failed
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # manual/scheduled
    trigger_user_id: Mapped[int | None] = mapped_column(Integer)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    total_resources: Mapped[int] = mapped_column(Integer, default=0)
    risk_count: Mapped[dict | None] = mapped_column(JSONB)  # {"critical": 3, "high": 9, ...}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 7: 创建 app/models/risk.py**

```python
from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RiskItem(Base):
    __tablename__ = "risk_items"
    __table_args__ = (
        Index("idx_risk_inspection", "inspection_id"),
        Index("idx_risk_status", "status"),
        Index("idx_risk_level", "risk_level"),
        Index("idx_risk_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspection_tasks.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cloud_provider: Mapped[str | None] = mapped_column(String(20))  # aliyun/tencent/huawei/idc
    region: Mapped[str | None] = mapped_column(String(64))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"))
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_title: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_detail: Mapped[str | None] = mapped_column(Text)
    metric_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[int | None] = mapped_column(Integer)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RiskItemArchive(Base):
    """30天前的风险项归档表，结构与 RiskItem 相同，不做实时查询"""
    __tablename__ = "risk_items_archive"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cloud_provider: Mapped[str | None] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(64))
    rule_id: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_title: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_detail: Mapped[str | None] = mapped_column(Text)
    metric_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[int | None] = mapped_column(Integer)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    archived_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
```

- [ ] **Step 8: 创建 app/models/__init__.py**

```python
from app.database import Base
from app.models.user import User
from app.models.rule import Rule
from app.models.inspection import InspectionTask
from app.models.risk import RiskItem, RiskItemArchive

__all__ = ["Base", "User", "Rule", "InspectionTask", "RiskItem", "RiskItemArchive"]
```

- [ ] **Step 9: 运行测试确认通过**

```bash
pytest tests/test_models.py -v
```

期望输出：
```
tests/test_models.py::test_user_model_fields PASSED
tests/test_models.py::test_rule_model_fields PASSED
```

- [ ] **Step 10: 配置 Alembic 并生成初始迁移**

创建 `backend/alembic.ini`（仅修改 script_location 和 sqlalchemy.url 行）：

```ini
[alembic]
script_location = migrations
sqlalchemy.url = postgresql://inspector:password@localhost:5432/inspection

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

创建 `backend/migrations/env.py`：

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

执行迁移：

```bash
cd backend
alembic revision --autogenerate -m "initial_schema"
alembic upgrade head
```

期望输出：`Running upgrade  -> xxxx, initial_schema`

- [ ] **Step 11: Commit**

```bash
git add backend/app/database.py backend/app/models/ backend/alembic.ini backend/migrations/ backend/tests/
git commit -m "feat: add database models and alembic migrations"
```

---

## Task 3: JWT 认证与用户管理

**Files:**
- Create: `backend/app/services/auth.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/api/deps.py`
- Create: `backend/app/api/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_auth.py
import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_login_success(client, seed_admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "Admin123!"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client, seed_admin_user):
    response = await client.post("/api/v1/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_without_token(client):
    response = await client.get("/api/v1/inspection/latest")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_token(client, admin_token):
    response = await client.get("/api/v1/inspection/latest", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert response.status_code == 200
```

在 `conftest.py` 中补充 fixtures：

```python
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.auth import get_password_hash, create_access_token
from app.models.user import User


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_admin_user(db):
    user = User(
        username="admin",
        password_hash=get_password_hash("Admin123!"),
        email="admin@example.com",
        role="admin",
    )
    db.add(user)
    await db.commit()
    return user


@pytest_asyncio.fixture
async def admin_token(seed_admin_user):
    return create_access_token({"sub": "admin", "role": "admin"})
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_auth.py -v
```

期望输出：`ImportError: cannot import name 'get_password_hash'`

- [ ] **Step 3: 创建 app/services/auth.py**

```python
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """解码 JWT，失败时抛出 JWTError"""
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
```

- [ ] **Step 4: 创建 app/schemas/auth.py**

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
```

- [ ] **Step 5: 创建 app/api/deps.py**

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.user import User
from app.services.auth import decode_access_token

bearer_scheme = HTTPBearer()


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    result = await db.execute(select(User).where(User.username == username, User.is_active == True))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


def require_role(*roles: str):
    async def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return current_user
    return checker
```

- [ ] **Step 6: 创建 app/api/auth.py**

```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import verify_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).where(User.username == body.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = create_access_token({"sub": user.username, "role": user.role})
    return TokenResponse(access_token=token, role=user.role)
```

- [ ] **Step 7: 创建 app/main.py**

```python
from fastapi import FastAPI
from app.api import auth

app = FastAPI(title="运维巡检系统", version="1.0.0")

app.include_router(auth.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: 运行测试确认通过**

```bash
pytest tests/test_auth.py -v
```

期望输出：
```
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_login_wrong_password PASSED
tests/test_auth.py::test_protected_route_without_token PASSED
tests/test_auth.py::test_protected_route_with_token PASSED
```

- [ ] **Step 9: Commit**

```bash
git add backend/app/services/ backend/app/schemas/auth.py backend/app/api/ backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: add JWT auth, RBAC deps, login endpoint"
```

---

## Task 4: 采集器基类与 Prometheus 采集器

**Files:**
- Create: `backend/app/collectors/base.py`
- Create: `backend/app/collectors/prometheus.py`
- Create: `backend/app/collectors/__init__.py`
- Create: `backend/tests/test_prometheus_collector.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_prometheus_collector.py
import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.prometheus import PrometheusCollector
from app.collectors.base import HostMetric, DBMetric


@pytest.mark.asyncio
async def test_collect_hosts_returns_host_metrics():
    mock_response = [
        {
            "metric": {"instance": "192.168.1.47:9100", "job": "node"},
            "value": [1700000000, "0.72"]
        }
    ]
    with patch("app.collectors.prometheus.PrometheusCollector._query", new_callable=AsyncMock) as mock_query:
        mock_query.return_value = mock_response
        collector = PrometheusCollector(url="http://fake:9090")
        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "192.168.1.47:9100"
    assert hosts[0].cpu_usage_percent == pytest.approx(72.0, abs=0.1)
    assert hosts[0].cloud_provider == "idc"


@pytest.mark.asyncio
async def test_collect_hosts_empty_on_prometheus_error():
    with patch("app.collectors.prometheus.PrometheusCollector._query", new_callable=AsyncMock) as mock_query:
        mock_query.side_effect = Exception("connection refused")
        collector = PrometheusCollector(url="http://fake:9090")
        hosts = await collector.collect_hosts()

    assert hosts == []
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_prometheus_collector.py -v
```

期望输出：`ModuleNotFoundError: No module named 'app.collectors'`

- [ ] **Step 3: 创建 app/collectors/base.py**

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HostMetric:
    resource_id: str          # 唯一标识，如 IP:port 或云实例 ID
    resource_name: str
    cloud_provider: str       # aliyun/tencent/huawei/idc
    region: Optional[str] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    load_average_1m: Optional[float] = None
    cpu_core_count: Optional[int] = None


@dataclass
class DBMetric:
    resource_id: str
    resource_name: str
    db_type: str              # mysql/mongodb/redis
    cloud_provider: str
    region: Optional[str] = None
    # MySQL
    connection_count: Optional[int] = None
    max_connections: Optional[int] = None
    slow_query_count: Optional[int] = None
    replication_delay_seconds: Optional[float] = None
    # Redis
    memory_usage_percent: Optional[float] = None
    hit_rate_percent: Optional[float] = None
    # MongoDB
    replica_set_healthy: Optional[bool] = None


@dataclass
class ContainerMetric:
    resource_id: str          # namespace/pod_name
    resource_name: str
    cloud_provider: str
    cluster_name: str
    namespace: str
    region: Optional[str] = None
    pod_status: Optional[str] = None      # Running/Pending/CrashLoopBackOff
    restart_count: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    node_ready: Optional[bool] = None     # Node 健康度（Node 级别才填）


class BaseCollector(ABC):
    @abstractmethod
    async def collect_hosts(self) -> list[HostMetric]:
        """采集主机指标，失败时返回空列表（不抛出异常）"""

    @abstractmethod
    async def collect_databases(self) -> list[DBMetric]:
        """采集数据库指标，失败时返回空列表"""

    @abstractmethod
    async def collect_containers(self) -> list[ContainerMetric]:
        """采集容器指标，失败时返回空列表"""
```

- [ ] **Step 4: 创建 app/collectors/prometheus.py**

```python
import logging
import httpx
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class PrometheusCollector(BaseCollector):
    """从 IDC 自建 Prometheus 采集主机指标"""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    async def _query(self, promql: str) -> list[dict]:
        """执行 PromQL 即时查询，返回 result 列表"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.url}/api/v1/query",
                params={"query": promql},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("result", [])

    async def collect_hosts(self) -> list[HostMetric]:
        try:
            cpu_results = await self._query(
                '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
            )
            mem_results = await self._query(
                '100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)'
            )
            disk_results = await self._query(
                '100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)'
            )
            load_results = await self._query("node_load1")
            cpu_cores_results = await self._query('count by (instance) (node_cpu_seconds_total{mode="idle"})')
        except Exception as e:
            logger.error("PrometheusCollector.collect_hosts failed: %s", e)
            return []

        # 以 CPU 结果为基准构建 metric 字典
        cpu_map = {r["metric"]["instance"]: float(r["value"][1]) for r in cpu_results}
        mem_map = {r["metric"]["instance"]: float(r["value"][1]) for r in mem_results}
        disk_map = {r["metric"]["instance"]: float(r["value"][1]) for r in disk_results}
        load_map = {r["metric"]["instance"]: float(r["value"][1]) for r in load_results}
        cores_map = {r["metric"]["instance"]: int(float(r["value"][1])) for r in cpu_cores_results}

        metrics = []
        for instance, cpu in cpu_map.items():
            metrics.append(HostMetric(
                resource_id=instance,
                resource_name=instance.split(":")[0],
                cloud_provider="idc",
                cpu_usage_percent=round(cpu, 2),
                memory_usage_percent=round(mem_map.get(instance, 0), 2),
                disk_usage_percent=round(disk_map.get(instance, 0), 2),
                load_average_1m=round(load_map.get(instance, 0), 2),
                cpu_core_count=cores_map.get(instance),
            ))
        return metrics

    async def collect_databases(self) -> list[DBMetric]:
        # Phase 1 仅实现 Prometheus 主机采集，数据库由云平台 SDK 采集（Phase 2）
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        # Phase 1 K8s 采集在 Phase 2 实现
        return []
```

- [ ] **Step 5: 创建 app/collectors/__init__.py**

```python
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric
from app.collectors.prometheus import PrometheusCollector

__all__ = ["BaseCollector", "HostMetric", "DBMetric", "ContainerMetric", "PrometheusCollector"]
```

- [ ] **Step 6: 运行测试确认通过**

```bash
pytest tests/test_prometheus_collector.py -v
```

期望输出：
```
tests/test_prometheus_collector.py::test_collect_hosts_returns_host_metrics PASSED
tests/test_prometheus_collector.py::test_collect_hosts_empty_on_prometheus_error PASSED
```

- [ ] **Step 7: Commit**

```bash
git add backend/app/collectors/ backend/tests/test_prometheus_collector.py
git commit -m "feat: add BaseCollector interface and PrometheusCollector"
```

---

## Task 5: 规则引擎

**Files:**
- Create: `backend/app/engine/rule_engine.py`
- Create: `backend/app/engine/__init__.py`
- Create: `backend/tests/test_rule_engine.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_rule_engine.py
import pytest
from app.engine.rule_engine import RuleEngine, RuleMatch
from app.collectors.base import HostMetric
from app.models.rule import Rule


def make_rule(rule_code, metric_name, operator, threshold, risk_level, resource_type="host"):
    rule = Rule()
    rule.id = 1
    rule.rule_code = rule_code
    rule.rule_name = rule_code
    rule.resource_type = resource_type
    rule.metric_name = metric_name
    rule.operator = operator
    rule.threshold_value = threshold
    rule.risk_level = risk_level
    rule.enabled = True
    rule.description = ""
    return rule


def test_cpu_critical_rule_matches():
    rules = [make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=92.0,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 1
    assert matches[0].risk_level == "critical"
    assert matches[0].metric_value == 92.0


def test_cpu_normal_no_match():
    rules = [make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=50.0,
    )
    matches = engine.evaluate_host(metric)
    assert matches == []


def test_multiple_rules_multiple_matches():
    rules = [
        make_rule("host_cpu_high", "cpu_usage_percent", ">", 80.0, "high"),
        make_rule("host_disk_critical", "disk_usage_percent", ">", 90.0, "critical"),
    ]
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=85.0,
        disk_usage_percent=95.0,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 2


def test_disabled_rule_skipped():
    rule = make_rule("host_cpu_critical", "cpu_usage_percent", ">", 90.0, "critical")
    rule.enabled = False
    engine = RuleEngine([rule])
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        cpu_usage_percent=99.0,
    )
    matches = engine.evaluate_host(metric)
    assert matches == []


def test_load_average_rule_with_core_count():
    """系统负载 > CPU核心数*2 触发告警"""
    rules = [make_rule("host_load_high", "load_average_1m", ">", 0, "high")]
    # 特殊规则：阈值由 cpu_core_count * 2 动态计算，threshold_value=0 表示动态
    engine = RuleEngine(rules)
    metric = HostMetric(
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        load_average_1m=10.0,
        cpu_core_count=4,
    )
    matches = engine.evaluate_host(metric)
    assert len(matches) == 1
    assert matches[0].threshold_value == 8.0  # 4 * 2
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_rule_engine.py -v
```

期望输出：`ModuleNotFoundError: No module named 'app.engine'`

- [ ] **Step 3: 创建 app/engine/rule_engine.py**

```python
import operator as op
from dataclasses import dataclass
from typing import Optional
from app.collectors.base import HostMetric, DBMetric, ContainerMetric
from app.models.rule import Rule

OPERATORS = {
    ">": op.gt,
    "<": op.lt,
    ">=": op.ge,
    "<=": op.le,
    "==": op.eq,
    "!=": op.ne,
}

# host metric 字段映射：rule.metric_name -> HostMetric 属性名
HOST_METRIC_MAP = {
    "cpu_usage_percent": "cpu_usage_percent",
    "memory_usage_percent": "memory_usage_percent",
    "disk_usage_percent": "disk_usage_percent",
    "load_average_1m": "load_average_1m",
}


@dataclass
class RuleMatch:
    rule: Rule
    risk_level: str
    risk_title: str
    risk_detail: str
    metric_value: float
    threshold_value: float


class RuleEngine:
    def __init__(self, rules: list[Rule]):
        self.rules = [r for r in rules if r.enabled]

    def _compare(self, value: float, operator: str, threshold: float) -> bool:
        fn = OPERATORS.get(operator)
        if fn is None:
            return False
        return fn(value, threshold)

    def evaluate_host(self, metric: HostMetric) -> list[RuleMatch]:
        matches = []
        host_rules = [r for r in self.rules if r.resource_type == "host"]

        for rule in host_rules:
            attr = HOST_METRIC_MAP.get(rule.metric_name)
            if attr is None:
                continue
            value = getattr(metric, attr, None)
            if value is None:
                continue

            # 系统负载特殊处理：阈值=0 表示动态阈值 cpu_core_count * 2
            threshold = rule.threshold_value
            if rule.metric_name == "load_average_1m" and threshold == 0:
                if metric.cpu_core_count is None:
                    continue
                threshold = metric.cpu_core_count * 2.0

            if self._compare(value, rule.operator, threshold):
                matches.append(RuleMatch(
                    rule=rule,
                    risk_level=rule.risk_level,
                    risk_title=f"{metric.resource_name} {rule.rule_name}（当前值: {value:.1f}，阈值: {threshold:.1f}）",
                    risk_detail=rule.description or "",
                    metric_value=value,
                    threshold_value=threshold,
                ))
        return matches

    def evaluate_database(self, metric: DBMetric) -> list[RuleMatch]:
        # Phase 2 实现，Phase 1 返回空
        return []

    def evaluate_container(self, metric: ContainerMetric) -> list[RuleMatch]:
        # Phase 2 实现，Phase 1 返回空
        return []
```

- [ ] **Step 4: 创建 app/engine/__init__.py**

```python
from app.engine.rule_engine import RuleEngine, RuleMatch

__all__ = ["RuleEngine", "RuleMatch"]
```

- [ ] **Step 5: 运行测试确认通过**

```bash
pytest tests/test_rule_engine.py -v
```

期望输出：
```
tests/test_rule_engine.py::test_cpu_critical_rule_matches PASSED
tests/test_rule_engine.py::test_cpu_normal_no_match PASSED
tests/test_rule_engine.py::test_multiple_rules_multiple_matches PASSED
tests/test_rule_engine.py::test_disabled_rule_skipped PASSED
tests/test_rule_engine.py::test_load_average_rule_with_core_count PASSED
```

- [ ] **Step 6: Commit**

```bash
git add backend/app/engine/ backend/tests/test_rule_engine.py
git commit -m "feat: add RuleEngine with host metric evaluation"
```

---

## Task 6: Celery 配置与巡检任务

**Files:**
- Create: `backend/app/tasks/celery_app.py`
- Create: `backend/app/tasks/inspection_task.py`
- Create: `backend/app/tasks/cleanup_task.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/tests/test_inspection_task.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_inspection_task.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.tasks.inspection_task import run_inspection_sync


@pytest.mark.asyncio
async def test_run_inspection_creates_task_record(db):
    with patch("app.tasks.inspection_task.PrometheusCollector") as MockCollector:
        instance = MockCollector.return_value
        instance.collect_hosts = AsyncMock(return_value=[])
        instance.collect_databases = AsyncMock(return_value=[])
        instance.collect_containers = AsyncMock(return_value=[])

        task_id = await run_inspection_sync(db=db, trigger_type="manual", trigger_user_id=None)

    from sqlalchemy import select
    from app.models.inspection import InspectionTask
    result = await db.execute(select(InspectionTask).where(InspectionTask.task_id == task_id))
    task = result.scalar_one_or_none()
    assert task is not None
    assert task.status == "completed"
    assert task.trigger_type == "manual"


@pytest.mark.asyncio
async def test_run_inspection_saves_risk_items(db, seed_rules):
    from app.collectors.base import HostMetric
    mock_host = HostMetric(
        resource_id="192.168.1.47:9100",
        resource_name="192.168.1.47",
        cloud_provider="idc",
        cpu_usage_percent=95.0,  # 超过 critical 阈值 90%
    )
    with patch("app.tasks.inspection_task.PrometheusCollector") as MockCollector:
        instance = MockCollector.return_value
        instance.collect_hosts = AsyncMock(return_value=[mock_host])
        instance.collect_databases = AsyncMock(return_value=[])
        instance.collect_containers = AsyncMock(return_value=[])

        await run_inspection_sync(db=db, trigger_type="manual", trigger_user_id=None)

    from sqlalchemy import select
    from app.models.risk import RiskItem
    result = await db.execute(select(RiskItem).where(RiskItem.risk_level == "critical"))
    risks = result.scalars().all()
    assert len(risks) >= 1
    assert risks[0].resource_id == "192.168.1.47:9100"
```

在 `conftest.py` 补充：

```python
@pytest_asyncio.fixture
async def seed_rules(db):
    from app.models.rule import Rule
    rules = [
        Rule(rule_code="host_cpu_critical", rule_name="CPU严重", resource_type="host",
             metric_name="cpu_usage_percent", operator=">", threshold_value=90.0, risk_level="critical"),
        Rule(rule_code="host_disk_high", rule_name="磁盘高危", resource_type="host",
             metric_name="disk_usage_percent", operator=">", threshold_value=85.0, risk_level="high"),
    ]
    for r in rules:
        db.add(r)
    await db.commit()
    return rules
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_inspection_task.py -v
```

期望输出：`ModuleNotFoundError`

- [ ] **Step 3: 创建 app/tasks/celery_app.py**

```python
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "inspection",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.inspection_task", "app.tasks.cleanup_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "daily-inspection": {
            "task": "app.tasks.inspection_task.run_inspection",
            "schedule": crontab(hour=8, minute=0),
            "kwargs": {"trigger_type": "scheduled"},
        },
        "cleanup-old-risks": {
            "task": "app.tasks.cleanup_task.archive_old_risks",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
```

- [ ] **Step 4: 创建 app/tasks/inspection_task.py**

```python
import asyncio
import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.inspection import InspectionTask
from app.models.risk import RiskItem
from app.models.rule import Rule
from app.collectors.prometheus import PrometheusCollector
from app.engine.rule_engine import RuleEngine
from app.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def run_inspection_sync(
    db: AsyncSession,
    trigger_type: str,
    trigger_user_id: int | None,
) -> str:
    """核心巡检逻辑（async），供 Celery task 和测试调用"""
    task_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    # 1. 创建巡检记录
    inspection = InspectionTask(
        task_id=task_id,
        status="running",
        trigger_type=trigger_type,
        trigger_user_id=trigger_user_id,
        start_time=start_time,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    try:
        # 2. 并发采集
        collector = PrometheusCollector(url=settings.prometheus_url)
        host_metrics, db_metrics, container_metrics = await asyncio.gather(
            collector.collect_hosts(),
            collector.collect_databases(),
            collector.collect_containers(),
        )

        # 3. 加载规则
        result = await db.execute(select(Rule).where(Rule.enabled == True))
        rules = result.scalars().all()
        engine = RuleEngine(rules)

        # 4. 规则匹配，生成风险项
        risk_items = []
        for metric in host_metrics:
            for match in engine.evaluate_host(metric):
                risk_items.append(RiskItem(
                    inspection_id=inspection.id,
                    resource_type="host",
                    resource_id=metric.resource_id,
                    resource_name=metric.resource_name,
                    cloud_provider=metric.cloud_provider,
                    region=metric.region,
                    rule_id=match.rule.id,
                    risk_level=match.risk_level,
                    risk_title=match.risk_title,
                    risk_detail=match.risk_detail,
                    metric_value=match.metric_value,
                    threshold_value=match.threshold_value,
                    status="pending",
                ))

        db.add_all(risk_items)

        # 5. 统计风险数量
        risk_count: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in risk_items:
            risk_count[item.risk_level] = risk_count.get(item.risk_level, 0) + 1

        # 6. 更新巡检记录
        inspection.status = "completed"
        inspection.end_time = datetime.utcnow()
        inspection.total_resources = len(host_metrics) + len(db_metrics) + len(container_metrics)
        inspection.risk_count = risk_count
        await db.commit()

    except Exception as e:
        logger.error("Inspection %s failed: %s", task_id, e)
        inspection.status = "failed"
        inspection.end_time = datetime.utcnow()
        await db.commit()

    return task_id


@celery_app.task(name="app.tasks.inspection_task.run_inspection", bind=True)
def run_inspection(self, trigger_type: str = "scheduled", trigger_user_id: int | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            return await run_inspection_sync(db, trigger_type, trigger_user_id)
    return asyncio.run(_run())
```

- [ ] **Step 5: 创建 app/tasks/cleanup_task.py**

```python
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, delete, insert
from app.database import AsyncSessionLocal
from app.models.risk import RiskItem, RiskItemArchive
from app.models.inspection import InspectionTask
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


async def _archive_old_risks_async():
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    async with AsyncSessionLocal() as db:
        # 查询需要归档的记录
        result = await db.execute(
            select(RiskItem).where(RiskItem.created_at < cutoff)
        )
        old_items = result.scalars().all()

        if not old_items:
            logger.info("No risk items to archive")
            return 0

        # 插入归档表
        archive_rows = [
            {c.key: getattr(item, c.key) for c in RiskItem.__table__.columns}
            for item in old_items
        ]
        await db.execute(insert(RiskItemArchive), archive_rows)

        # 从主表删除
        ids = [item.id for item in old_items]
        await db.execute(delete(RiskItem).where(RiskItem.id.in_(ids)))

        # 同步清理 inspection_tasks
        await db.execute(
            delete(InspectionTask).where(InspectionTask.created_at < cutoff)
        )

        await db.commit()
        logger.info("Archived %d risk items older than %d days", len(ids), RETENTION_DAYS)
        return len(ids)


@celery_app.task(name="app.tasks.cleanup_task.archive_old_risks")
def archive_old_risks():
    return asyncio.run(_archive_old_risks_async())
```

- [ ] **Step 6: 创建 app/tasks/__init__.py**

```python
```

- [ ] **Step 7: 运行测试确认通过**

```bash
pytest tests/test_inspection_task.py -v
```

期望输出：
```
tests/test_inspection_task.py::test_run_inspection_creates_task_record PASSED
tests/test_inspection_task.py::test_run_inspection_saves_risk_items PASSED
```

- [ ] **Step 8: Commit**

```bash
git add backend/app/tasks/ backend/tests/test_inspection_task.py
git commit -m "feat: add Celery tasks for inspection and cleanup"
```

---

## Task 7: 巡检 API、风险 API、规则 API

**Files:**
- Create: `backend/app/schemas/inspection.py`
- Create: `backend/app/schemas/risk.py`
- Create: `backend/app/schemas/rule.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/api/inspection.py`
- Create: `backend/app/api/risks.py`
- Create: `backend/app/api/rules.py`
- Modify: `backend/app/main.py`
- Create: `backend/tests/test_inspection_api.py`
- Create: `backend/tests/test_risks_api.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_inspection_api.py
import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_trigger_inspection_returns_task_id(client, admin_token):
    with patch("app.api.inspection.run_inspection_sync", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = "test-task-uuid"
        response = await client.post(
            "/api/v1/inspection/trigger",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    assert response.status_code == 202
    data = response.json()
    assert data["task_id"] == "test-task-uuid"
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_trigger_inspection_requires_auth(client):
    response = await client.post("/api/v1/inspection/trigger")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_latest_inspection_empty(client, admin_token):
    response = await client.get(
        "/api/v1/inspection/latest",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["task"] is None


# backend/tests/test_risks_api.py
@pytest.mark.asyncio
async def test_list_risks_empty(client, admin_token):
    response = await client.get(
        "/api/v1/risks",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_update_risk_status(client, admin_token, db, seed_inspection_with_risk):
    risk_id = seed_inspection_with_risk
    response = await client.patch(
        f"/api/v1/risks/{risk_id}/status",
        json={"status": "processing"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processing"


@pytest.mark.asyncio
async def test_update_risk_invalid_status(client, admin_token, db, seed_inspection_with_risk):
    risk_id = seed_inspection_with_risk
    response = await client.patch(
        f"/api/v1/risks/{risk_id}/status",
        json={"status": "invalid_status"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert response.status_code == 422
```

在 `conftest.py` 补充：

```python
@pytest_asyncio.fixture
async def seed_inspection_with_risk(db):
    from app.models.inspection import InspectionTask
    from app.models.risk import RiskItem
    import uuid
    task = InspectionTask(
        task_id=str(uuid.uuid4()),
        status="completed",
        trigger_type="manual",
        total_resources=1,
        risk_count={"critical": 1, "high": 0, "medium": 0, "low": 0},
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    risk = RiskItem(
        inspection_id=task.id,
        resource_type="host",
        resource_id="192.168.1.1:9100",
        resource_name="192.168.1.1",
        cloud_provider="idc",
        risk_level="critical",
        risk_title="CPU使用率95%",
        metric_value=95.0,
        threshold_value=90.0,
        status="pending",
    )
    db.add(risk)
    await db.commit()
    await db.refresh(risk)
    return risk.id
```

- [ ] **Step 2: 运行测试确认失败**

```bash
pytest tests/test_inspection_api.py tests/test_risks_api.py -v
```

期望输出：`ImportError` 或 404 错误

- [ ] **Step 3: 创建 Pydantic schemas**

`backend/app/schemas/inspection.py`:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InspectionTriggerResponse(BaseModel):
    task_id: str
    status: str


class InspectionTaskResponse(BaseModel):
    id: int
    task_id: str
    status: str
    trigger_type: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    total_resources: int
    risk_count: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class LatestInspectionResponse(BaseModel):
    task: Optional[InspectionTaskResponse]
```

`backend/app/schemas/risk.py`:

```python
from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel

RiskStatus = Literal["pending", "processing", "ignored", "resolved"]


class RiskItemResponse(BaseModel):
    id: int
    inspection_id: int
    resource_type: str
    resource_id: str
    resource_name: str
    cloud_provider: Optional[str]
    risk_level: str
    risk_title: str
    risk_detail: Optional[str]
    metric_value: Optional[float]
    threshold_value: Optional[float]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskStatusUpdate(BaseModel):
    status: RiskStatus


class RiskListResponse(BaseModel):
    items: list[RiskItemResponse]
    total: int
```

`backend/app/schemas/rule.py`:

```python
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RuleResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    resource_type: str
    metric_name: str
    operator: str
    threshold_value: float
    risk_level: str
    enabled: bool
    description: Optional[str]

    model_config = {"from_attributes": True}


class RuleUpdate(BaseModel):
    threshold_value: Optional[float] = None
    enabled: Optional[bool] = None
```

`backend/app/schemas/__init__.py`:

```python
```

- [ ] **Step 4: 创建 app/api/inspection.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.inspection import InspectionTask
from app.schemas.inspection import InspectionTriggerResponse, LatestInspectionResponse, InspectionTaskResponse
from app.tasks.inspection_task import run_inspection_sync

router = APIRouter(prefix="/api/v1/inspection", tags=["inspection"])


@router.post("/trigger", response_model=InspectionTriggerResponse, status_code=202)
async def trigger_inspection(
    current_user: User = Depends(require_role("admin", "ops")),
    db: AsyncSession = Depends(get_db),
):
    task_id = await run_inspection_sync(db, trigger_type="manual", trigger_user_id=current_user.id)
    return InspectionTriggerResponse(task_id=task_id, status="running")


@router.get("/latest", response_model=LatestInspectionResponse)
async def get_latest_inspection(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InspectionTask).order_by(desc(InspectionTask.created_at)).limit(1)
    )
    task = result.scalar_one_or_none()
    return LatestInspectionResponse(task=InspectionTaskResponse.model_validate(task) if task else None)


@router.get("/history", response_model=list[InspectionTaskResponse])
async def get_inspection_history(
    limit: int = 30,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InspectionTask).order_by(desc(InspectionTask.created_at)).limit(limit)
    )
    return result.scalars().all()
```

- [ ] **Step 5: 创建 app/api/risks.py**

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.risk import RiskItem
from app.schemas.risk import RiskItemResponse, RiskStatusUpdate, RiskListResponse

router = APIRouter(prefix="/api/v1/risks", tags=["risks"])


@router.get("", response_model=RiskListResponse)
async def list_risks(
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    cloud_provider: str | None = Query(None),
    resource_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(RiskItem)
    if risk_level:
        query = query.where(RiskItem.risk_level == risk_level)
    if status:
        query = query.where(RiskItem.status == status)
    if cloud_provider:
        query = query.where(RiskItem.cloud_provider == cloud_provider)
    if resource_type:
        query = query.where(RiskItem.resource_type == resource_type)

    # dev 角色只能看自己负责的服务
    if current_user.role == "dev" and current_user.responsible_services:
        services = current_user.responsible_services
        query = query.where(RiskItem.resource_name.in_(services))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return RiskListResponse(items=items, total=total)


@router.patch("/{risk_id}/status", response_model=RiskItemResponse)
async def update_risk_status(
    risk_id: int,
    body: RiskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskItem).where(RiskItem.id == risk_id))
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk item not found")

    risk.status = body.status
    await db.commit()
    await db.refresh(risk)
    return risk
```

- [ ] **Step 6: 创建 app/api/rules.py**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.rule import Rule
from app.schemas.rule import RuleResponse, RuleUpdate

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rule))
    return result.scalars().all()


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    body: RuleUpdate,
    _: User = Depends(require_role("admin", "ops")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if body.threshold_value is not None:
        rule.threshold_value = body.threshold_value
    if body.enabled is not None:
        rule.enabled = body.enabled

    await db.commit()
    await db.refresh(rule)
    return rule
```

- [ ] **Step 7: 更新 app/main.py 注册所有路由**

```python
from fastapi import FastAPI
from app.api import auth, inspection, risks, rules

app = FastAPI(title="运维巡检系统", version="1.0.0")

app.include_router(auth.router)
app.include_router(inspection.router)
app.include_router(risks.router)
app.include_router(rules.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 8: 运行所有测试确认通过**

```bash
pytest tests/ -v
```

期望输出：全部 PASSED，无 FAILED

- [ ] **Step 9: Commit**

```bash
git add backend/app/schemas/ backend/app/api/inspection.py backend/app/api/risks.py backend/app/api/rules.py backend/app/main.py backend/tests/
git commit -m "feat: add inspection, risks, rules REST APIs"
```

---

## Task 8: 初始规则种子数据与 Dockerfile

**Files:**
- Create: `backend/migrations/versions/0002_seed_rules.py`
- Create: `backend/Dockerfile`

- [ ] **Step 1: 创建规则种子迁移**

```python
# backend/migrations/versions/0002_seed_rules.py
"""seed default inspection rules

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-15
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '0002'
down_revision = '0001'


def upgrade() -> None:
    now = datetime.utcnow()
    op.bulk_insert(
        sa.table('rules',
            sa.column('rule_code', sa.String),
            sa.column('rule_name', sa.String),
            sa.column('resource_type', sa.String),
            sa.column('metric_name', sa.String),
            sa.column('operator', sa.String),
            sa.column('threshold_value', sa.Float),
            sa.column('risk_level', sa.String),
            sa.column('enabled', sa.Boolean),
            sa.column('description', sa.Text),
            sa.column('created_at', sa.DateTime),
            sa.column('updated_at', sa.DateTime),
        ),
        [
            # 主机规则
            dict(rule_code='host_cpu_critical', rule_name='CPU使用率严重', resource_type='host',
                 metric_name='cpu_usage_percent', operator='>', threshold_value=90.0,
                 risk_level='critical', enabled=True, description='CPU使用率超过90%', created_at=now, updated_at=now),
            dict(rule_code='host_cpu_high', rule_name='CPU使用率高危', resource_type='host',
                 metric_name='cpu_usage_percent', operator='>', threshold_value=80.0,
                 risk_level='high', enabled=True, description='CPU使用率超过80%', created_at=now, updated_at=now),
            dict(rule_code='host_memory_critical', rule_name='内存使用率严重', resource_type='host',
                 metric_name='memory_usage_percent', operator='>', threshold_value=95.0,
                 risk_level='critical', enabled=True, description='内存使用率超过95%', created_at=now, updated_at=now),
            dict(rule_code='host_memory_high', rule_name='内存使用率高危', resource_type='host',
                 metric_name='memory_usage_percent', operator='>', threshold_value=85.0,
                 risk_level='high', enabled=True, description='内存使用率超过85%', created_at=now, updated_at=now),
            dict(rule_code='host_disk_critical', rule_name='磁盘使用率严重', resource_type='host',
                 metric_name='disk_usage_percent', operator='>', threshold_value=92.0,
                 risk_level='critical', enabled=True, description='磁盘使用率超过92%', created_at=now, updated_at=now),
            dict(rule_code='host_disk_high', rule_name='磁盘使用率高危', resource_type='host',
                 metric_name='disk_usage_percent', operator='>', threshold_value=85.0,
                 risk_level='high', enabled=True, description='磁盘使用率超过85%', created_at=now, updated_at=now),
            dict(rule_code='host_load_high', rule_name='系统负载高危', resource_type='host',
                 metric_name='load_average_1m', operator='>', threshold_value=0.0,
                 risk_level='high', enabled=True, description='系统负载超过CPU核心数*2，threshold_value=0表示动态阈值', created_at=now, updated_at=now),
        ]
    )


def downgrade() -> None:
    op.execute("DELETE FROM rules WHERE rule_code IN ('host_cpu_critical','host_cpu_high','host_memory_critical','host_memory_high','host_disk_critical','host_disk_high','host_load_high')")
```

执行迁移：

```bash
cd backend
alembic upgrade head
```

期望输出：`Running upgrade 0001 -> 0002`

- [ ] **Step 2: 创建 Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 默认启动 API 服务，Celery worker/beat 通过 command 覆盖
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 3: 运行完整测试套件验证覆盖率**

```bash
pytest tests/ -v --cov=app --cov-report=term-missing
```

期望输出：
- 全部测试 PASSED
- 覆盖率 > 80%

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0002_seed_rules.py backend/Dockerfile
git commit -m "feat: seed default rules, add Dockerfile"
```

---

## 自审核查

**Spec 覆盖对照：**
- ✅ 数据库模型（5张表）
- ✅ JWT 认证 + RBAC（admin/ops/dev）
- ✅ BaseCollector 接口 + PrometheusCollector
- ✅ RuleEngine（主机规则，包含动态负载阈值）
- ✅ Celery 巡检任务 + 定时清理任务
- ✅ REST API（trigger/latest/history/risks/rules）
- ✅ risk_items 清理策略（凌晨2点 Celery task）
- ✅ GIN 索引（users.responsible_services）
- ✅ dev 角色数据过滤
- ✅ 默认规则种子数据
- ✅ Dockerfile
- ⏭ 云平台采集器（Phase 2）
- ⏭ 邮件通知（Phase 2）
- ⏭ 前端（Phase 3）
- ⏭ Docker Compose / K8s（Phase 5）
