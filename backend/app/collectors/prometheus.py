import logging
import httpx
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class PrometheusCollector(BaseCollector):
    """从 IDC 自建 Prometheus 采集主机指标"""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    async def _query(self, promql: str) -> list[dict]:
        """执行 PromQL 即时查询，返回 result 列表"""
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.url}/api/v1/query",
                params={"query": promql},
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("result", [])

    async def collect_hosts(self) -> list[HostMetric]:
        try:
            cpu_results = await self._query(
                '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
            )
            mem_results = await self._query(
                '100 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes * 100)'
            )
            disk_results = await self._query(
                '100 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100)'
            )
            load_results = await self._query("node_load1")
            cpu_cores_results = await self._query('count by (instance) (node_cpu_seconds_total{mode="idle"})')
        except Exception as e:
            logger.error("PrometheusCollector.collect_hosts failed: %s", e)
            return []

        # 以 CPU 结果为基准构建 metric 字典
        cpu_map = {r["metric"]["instance"]: float(r["value"][1]) for r in cpu_results}
        mem_map = {r["metric"]["instance"]: float(r["value"][1]) for r in mem_results}
        disk_map = {r["metric"]["instance"]: float(r["value"][1]) for r in disk_results}
        load_map = {r["metric"]["instance"]: float(r["value"][1]) for r in load_results}
        cores_map = {r["metric"]["instance"]: int(float(r["value"][1])) for r in cpu_cores_results}

        metrics = []
        for instance, cpu in cpu_map.items():
            metrics.append(HostMetric(
                resource_id=instance,
                resource_name=instance.split(":")[0],
                cloud_provider="idc",
                cpu_usage_percent=round(cpu, 2),
                memory_usage_percent=round(mem_map.get(instance, 0), 2),
                disk_usage_percent=round(disk_map.get(instance, 0), 2),
                load_average_1m=round(load_map.get(instance, 0), 2),
                cpu_core_count=cores_map.get(instance),
            ))
        return metrics

    async def collect_databases(self) -> list[DBMetric]:
        # Phase 1 仅实现 Prometheus 主机采集，数据库由云平台 SDK 采集（Phase 2）
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        # Phase 1 K8s 采集在 Phase 2 实现
        return []
