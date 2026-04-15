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
