import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.prometheus import PrometheusCollector
from app.collectors.base import HostMetric, DBMetric


@pytest.mark.asyncio
async def test_collect_hosts_returns_host_metrics():
    mock_response = [
        {
            "metric": {"instance": "192.168.1.47:9100", "job": "node"},
            "value": [1700000000, "72.0"]
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
