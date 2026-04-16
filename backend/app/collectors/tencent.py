import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class TencentCollector(BaseCollector):
    def __init__(self, secret_id: str | None, secret_key: str | None, region: str):
        self._secret_id = secret_id
        self._secret_key = secret_key
        self.region = region

    async def _fetch_cvm_instances(self) -> list[dict]:
        return []

    async def _fetch_cvm_cpu(self) -> dict[str, float]:
        return {}

    async def collect_hosts(self) -> list[HostMetric]:
        try:
            instances = await self._fetch_cvm_instances()
            cpu_map = await self._fetch_cvm_cpu()
        except Exception as e:
            logger.error("TencentCollector.collect_hosts failed: %s", type(e).__name__)
            return []

        metrics: list[HostMetric] = []
        for item in instances:
            instance_id = item["instance_id"]
            metrics.append(
                HostMetric(
                    resource_id=instance_id,
                    resource_name=item.get("name", instance_id),
                    cloud_provider="tencent",
                    region=self.region,
                    cpu_usage_percent=cpu_map.get(instance_id),
                )
            )
        return metrics

    async def collect_databases(self) -> list[DBMetric]:
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        return []
