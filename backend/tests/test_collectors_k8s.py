import pytest
from unittest.mock import AsyncMock, patch

from app.collectors.k8s import K8sCollector
from app.collectors.base import ContainerMetric


@pytest.mark.asyncio
async def test_k8s_collect_containers_maps_metrics():
    collector = K8sCollector(config_mode="kubeconfig", kubeconfig_path=None)

    with patch.object(collector, "_fetch_pods", new_callable=AsyncMock) as mock_pods:
        mock_pods.return_value = [
            {
                "resource_id": "default/pod-a",
                "resource_name": "pod-a",
                "cluster_name": "cluster-1",
                "namespace": "default",
                "pod_status": "Running",
                "restart_count": 0,
            }
        ]

        containers = await collector.collect_containers()

    assert len(containers) == 1
    assert isinstance(containers[0], ContainerMetric)
    assert containers[0].resource_id == "default/pod-a"
    assert containers[0].resource_name == "pod-a"
    assert containers[0].cloud_provider == "k8s"
    assert containers[0].cluster_name == "cluster-1"
    assert containers[0].namespace == "default"
    assert containers[0].pod_status == "Running"
    assert containers[0].restart_count == 0


@pytest.mark.asyncio
async def test_k8s_collect_containers_returns_empty_on_error():
    collector = K8sCollector(config_mode="kubeconfig", kubeconfig_path=None)
    with patch.object(collector, "_fetch_pods", new_callable=AsyncMock) as mock_pods:
        mock_pods.side_effect = Exception("k8s api unavailable")
        containers = await collector.collect_containers()

    assert containers == []
