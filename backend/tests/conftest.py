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

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.auth import get_password_hash, create_access_token
from app.models.user import User


@pytest_asyncio.fixture
async def client(db):
    from app.api.deps import get_db

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


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
