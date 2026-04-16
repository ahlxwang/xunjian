import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class K8sCollector(BaseCollector):
    def __init__(self, config_mode: str = "kubeconfig", kubeconfig_path: str | None = None):
        self.config_mode = config_mode
        self.kubeconfig_path = kubeconfig_path

    async def _fetch_pods(self) -> list[dict]:
        return []

    async def collect_hosts(self) -> list[HostMetric]:
        return []

    async def collect_databases(self) -> list[DBMetric]:
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        try:
            pods = await self._fetch_pods()
            metrics: list[ContainerMetric] = []
            for pod in pods:
                metrics.append(
                    ContainerMetric(
                        resource_id=pod["resource_id"],
                        resource_name=pod["resource_name"],
                        cloud_provider="k8s",
                        cluster_name=pod.get("cluster_name", "default-cluster"),
                        namespace=pod.get("namespace", "default"),
                        pod_status=pod.get("pod_status"),
                        restart_count=pod.get("restart_count"),
                    )
                )
            return metrics
        except Exception as e:
            logger.error("K8sCollector.collect_containers failed: %s", type(e).__name__)
            return []
