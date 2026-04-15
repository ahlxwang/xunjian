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
