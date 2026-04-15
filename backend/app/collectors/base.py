from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class HostMetric:
    resource_id: str          # 唯一标识，如 IP:port 或云实例 ID
    resource_name: str
    cloud_provider: str       # aliyun/tencent/huawei/idc
    region: Optional[str] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None
    load_average_1m: Optional[float] = None
    cpu_core_count: Optional[int] = None


@dataclass
class DBMetric:
    resource_id: str
    resource_name: str
    db_type: str              # mysql/mongodb/redis
    cloud_provider: str
    region: Optional[str] = None
    # MySQL
    connection_count: Optional[int] = None
    max_connections: Optional[int] = None
    slow_query_count: Optional[int] = None
    replication_delay_seconds: Optional[float] = None
    # Redis
    memory_usage_percent: Optional[float] = None
    hit_rate_percent: Optional[float] = None
    # MongoDB
    replica_set_healthy: Optional[bool] = None


@dataclass
class ContainerMetric:
    resource_id: str          # namespace/pod_name
    resource_name: str
    cloud_provider: str
    cluster_name: str
    namespace: str
    region: Optional[str] = None
    pod_status: Optional[str] = None      # Running/Pending/CrashLoopBackOff
    restart_count: Optional[int] = None
    cpu_usage_percent: Optional[float] = None
    memory_usage_percent: Optional[float] = None
    node_ready: Optional[bool] = None     # Node 健康度（Node 级别才填）


class BaseCollector(ABC):
    @abstractmethod
    async def collect_hosts(self) -> list[HostMetric]:
        """采集主机指标，失败时返回空列表（不抛出异常）"""

    @abstractmethod
    async def collect_databases(self) -> list[DBMetric]:
        """采集数据库指标，失败时返回空列表"""

    @abstractmethod
    async def collect_containers(self) -> list[ContainerMetric]:
        """采集容器指标，失败时返回空列表"""
