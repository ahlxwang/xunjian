import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class AliyunCollector(BaseCollector):
    def __init__(self, access_key_id: str | None, access_key_secret: str | None, region: str):
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self.region = region

    async def _fetch_ecs_instances(self) -> list[dict]:
        return []

    async def _fetch_ecs_cpu(self) -> dict[str, float]:
        return {}

    async def _fetch_ecs_memory(self) -> dict[str, float]:
        return {}

    async def _fetch_ecs_disk(self) -> dict[str, float]:
        return {}

    async def collect_hosts(self) -> list[HostMetric]:
        try:
            instances = await self._fetch_ecs_instances()
            cpu_map = await self._fetch_ecs_cpu()
            mem_map = await self._fetch_ecs_memory()
            disk_map = await self._fetch_ecs_disk()
        except Exception as e:
            logger.error("AliyunCollector.collect_hosts failed: %s", type(e).__name__)
            return []

        metrics: list[HostMetric] = []
        for item in instances:
            instance_id = item["instance_id"]
            metrics.append(
                HostMetric(
                    resource_id=instance_id,
                    resource_name=item.get("name", instance_id),
                    cloud_provider="aliyun",
                    region=self.region,
                    cpu_usage_percent=cpu_map.get(instance_id),
                    memory_usage_percent=mem_map.get(instance_id),
                    disk_usage_percent=disk_map.get(instance_id),
                )
            )
        return metrics

    async def collect_databases(self) -> list[DBMetric]:
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        return []
