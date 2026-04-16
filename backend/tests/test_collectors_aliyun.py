import pytest
from unittest.mock import AsyncMock, patch

from app.collectors.aliyun import AliyunCollector
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_aliyun_collect_hosts_maps_metrics():
    collector = AliyunCollector(
        access_key_id="ak",
        access_key_secret="sk",
        region="cn-hangzhou",
    )

    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs, \
         patch.object(collector, "_fetch_ecs_cpu", new_callable=AsyncMock) as mock_cpu, \
         patch.object(collector, "_fetch_ecs_memory", new_callable=AsyncMock) as mock_mem, \
         patch.object(collector, "_fetch_ecs_disk", new_callable=AsyncMock) as mock_disk:
        mock_ecs.return_value = [{"instance_id": "i-001", "name": "ecs-1"}]
        mock_cpu.return_value = {"i-001": 81.2}
        mock_mem.return_value = {"i-001": 73.5}
        mock_disk.return_value = {"i-001": 62.1}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "i-001"
    assert hosts[0].resource_name == "ecs-1"
    assert hosts[0].cloud_provider == "aliyun"
    assert hosts[0].region == "cn-hangzhou"
    assert hosts[0].cpu_usage_percent == 81.2
    assert hosts[0].memory_usage_percent == 73.5
    assert hosts[0].disk_usage_percent == 62.1


@pytest.mark.asyncio
async def test_aliyun_collect_hosts_handles_missing_metrics():
    collector = AliyunCollector("ak", "sk", "cn-hangzhou")

    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs, \
         patch.object(collector, "_fetch_ecs_cpu", new_callable=AsyncMock) as mock_cpu, \
         patch.object(collector, "_fetch_ecs_memory", new_callable=AsyncMock) as mock_mem, \
         patch.object(collector, "_fetch_ecs_disk", new_callable=AsyncMock) as mock_disk:
        mock_ecs.return_value = [{"instance_id": "i-002", "name": "ecs-2"}]
        mock_cpu.return_value = {}
        mock_mem.return_value = {}
        mock_disk.return_value = {}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert hosts[0].resource_id == "i-002"
    assert hosts[0].cpu_usage_percent is None
    assert hosts[0].memory_usage_percent is None
    assert hosts[0].disk_usage_percent is None


@pytest.mark.asyncio
async def test_aliyun_collect_hosts_returns_empty_on_error():
    collector = AliyunCollector("ak", "sk", "cn-hangzhou")
    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs:
        mock_ecs.side_effect = Exception("sdk error")
        hosts = await collector.collect_hosts()

    assert hosts == []
