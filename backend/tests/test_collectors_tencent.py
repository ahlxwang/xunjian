import pytest
from unittest.mock import AsyncMock, patch

from app.collectors.tencent import TencentCollector
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_tencent_collect_hosts_maps_metrics():
    collector = TencentCollector("sid", "skey", "ap-guangzhou")

    with patch.object(collector, "_fetch_cvm_instances", new_callable=AsyncMock) as mock_cvm, \
         patch.object(collector, "_fetch_cvm_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_cvm.return_value = [{"instance_id": "ins-001", "name": "cvm-1"}]
        mock_cpu.return_value = {"ins-001": 66.6}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "ins-001"
    assert hosts[0].resource_name == "cvm-1"
    assert hosts[0].cloud_provider == "tencent"
    assert hosts[0].region == "ap-guangzhou"
    assert hosts[0].cpu_usage_percent == 66.6


@pytest.mark.asyncio
async def test_tencent_collect_hosts_handles_missing_metrics():
    collector = TencentCollector("sid", "skey", "ap-guangzhou")

    with patch.object(collector, "_fetch_cvm_instances", new_callable=AsyncMock) as mock_cvm, \
         patch.object(collector, "_fetch_cvm_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_cvm.return_value = [{"instance_id": "ins-002", "name": "cvm-2"}]
        mock_cpu.return_value = {}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert hosts[0].cpu_usage_percent is None


@pytest.mark.asyncio
async def test_tencent_collect_hosts_returns_empty_on_error():
    collector = TencentCollector("sid", "skey", "ap-guangzhou")
    with patch.object(collector, "_fetch_cvm_instances", new_callable=AsyncMock) as mock_cvm:
        mock_cvm.side_effect = Exception("api timeout")
        hosts = await collector.collect_hosts()

    assert hosts == []
