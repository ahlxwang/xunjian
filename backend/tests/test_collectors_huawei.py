import pytest
from unittest.mock import AsyncMock, patch

from app.collectors.huawei import HuaweiCollector
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_huawei_collect_hosts_maps_metrics():
    collector = HuaweiCollector("ak", "sk", "cn-north-4")

    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs, \
         patch.object(collector, "_fetch_ecs_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_ecs.return_value = [{"instance_id": "hw-001", "name": "ecs-hw-1"}]
        mock_cpu.return_value = {"hw-001": 55.0}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "hw-001"
    assert hosts[0].resource_name == "ecs-hw-1"
    assert hosts[0].cloud_provider == "huawei"
    assert hosts[0].region == "cn-north-4"
    assert hosts[0].cpu_usage_percent == 55.0


@pytest.mark.asyncio
async def test_huawei_collect_hosts_handles_missing_metrics():
    collector = HuaweiCollector("ak", "sk", "cn-north-4")

    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs, \
         patch.object(collector, "_fetch_ecs_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_ecs.return_value = [{"instance_id": "hw-002", "name": "ecs-hw-2"}]
        mock_cpu.return_value = {}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert hosts[0].cpu_usage_percent is None


@pytest.mark.asyncio
async def test_huawei_collect_hosts_returns_empty_on_error():
    collector = HuaweiCollector("ak", "sk", "cn-north-4")
    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs:
        mock_ecs.side_effect = Exception("auth failed")
        hosts = await collector.collect_hosts()

    assert hosts == []
