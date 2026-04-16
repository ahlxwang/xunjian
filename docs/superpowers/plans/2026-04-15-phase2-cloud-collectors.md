# Phase 2: Cloud Platform Collectors Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为运维巡检系统实现多云采集器（阿里云、腾讯云、华为云、K8s），统一采集主机/数据库/容器关键指标，并接入现有巡检任务流程。

**Architecture:** 在现有 `BaseCollector` 接口基础上新增 4 个具体采集器，采集逻辑与云 SDK 解耦，统一转换为 `HostMetric`、`DBMetric`、`ContainerMetric`。巡检任务中并发执行全部采集器并汇总结果，规则引擎继续复用现有能力。

**Tech Stack:** Python 3.10+, FastAPI, SQLAlchemy 2.0 (async), Celery, aliyun-python-sdk-core, tencentcloud-sdk-python, huaweicloudsdkcore, kubernetes, pytest, pytest-asyncio, unittest.mock

---

## 文件结构

```
backend/
├── app/
│   ├── config.py                          # 新增多云/K8s配置
│   ├── collectors/
│   │   ├── __init__.py                    # 导出新采集器
│   │   ├── aliyun.py                      # AliyunCollector
│   │   ├── tencent.py                     # TencentCollector
│   │   ├── huawei.py                      # HuaweiCollector
│   │   └── k8s.py                         # K8sCollector
│   └── tasks/
│       └── inspection_task.py             # 集成多采集器并发采集
├── tests/
│   ├── test_collectors_aliyun.py
│   ├── test_collectors_tencent.py
│   ├── test_collectors_huawei.py
│   ├── test_collectors_k8s.py
│   └── test_inspection_task_multi_collectors.py
└── requirements.txt                       # 增加SDK依赖
```

---

## Task 1: 增加云 SDK 依赖与配置项

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/.env.example`
- Modify: `backend/app/config.py`
- Create: `backend/tests/test_cloud_config.py`

- [ ] **Step 1: 写失败测试（配置项尚不存在）**

```python
# backend/tests/test_cloud_config.py
from app.config import Settings


def test_cloud_config_fields_present():
    settings = Settings.model_construct(
        database_url="postgresql+asyncpg://u:p@localhost:5432/db",
        redis_url="redis://localhost:6379/0",
        jwt_secret="x" * 32,
    )
    assert hasattr(settings, "aliyun_region")
    assert hasattr(settings, "tencent_region")
    assert hasattr(settings, "huawei_region")
    assert hasattr(settings, "k8s_config_mode")
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_cloud_config.py -v`

Expected: `AssertionError`（字段不存在）

- [ ] **Step 3: 更新 requirements.txt 增加 SDK 依赖**

在 `backend/requirements.txt` 追加：

```txt
aliyun-python-sdk-core==2.16.0
aliyun-python-sdk-cms==8.0.1
tencentcloud-sdk-python==3.0.1330
huaweicloudsdkcore==3.1.128
huaweicloudsdkces==3.1.128
kubernetes==29.0.0
```

- [ ] **Step 4: 更新 .env.example 增加多云/K8s变量**

在 `backend/.env.example` 追加：

```env
# Aliyun
ALIYUN_ACCESS_KEY_ID=
ALIYUN_ACCESS_KEY_SECRET=
ALIYUN_REGION=cn-hangzhou

# Tencent
TENCENT_SECRET_ID=
TENCENT_SECRET_KEY=
TENCENT_REGION=ap-guangzhou

# Huawei
HUAWEI_AK=
HUAWEI_SK=
HUAWEI_REGION=cn-north-4

# K8s collector mode: incluster|kubeconfig
K8S_CONFIG_MODE=kubeconfig
K8S_KUBECONFIG_PATH=
```

- [ ] **Step 5: 更新 app/config.py 添加配置字段**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    jwt_secret: str
    jwt_expire_minutes: int = 480
    prometheus_url: str = "http://localhost:9090"

    # Aliyun
    aliyun_access_key_id: str | None = None
    aliyun_access_key_secret: str | None = None
    aliyun_region: str = "cn-hangzhou"

    # Tencent
    tencent_secret_id: str | None = None
    tencent_secret_key: str | None = None
    tencent_region: str = "ap-guangzhou"

    # Huawei
    huawei_ak: str | None = None
    huawei_sk: str | None = None
    huawei_region: str = "cn-north-4"

    # K8s
    k8s_config_mode: str = "kubeconfig"
    k8s_kubeconfig_path: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
```

- [ ] **Step 6: 运行测试确认通过**

Run: `pytest tests/test_cloud_config.py -v`

Expected:
```
tests/test_cloud_config.py::test_cloud_config_fields_present PASSED
```

- [ ] **Step 7: Commit**

```bash
git add backend/requirements.txt backend/.env.example backend/app/config.py backend/tests/test_cloud_config.py
git commit -m "feat: add cloud collector dependencies and config"
```

---

## Task 2: 实现 AliyunCollector（ECS/RDS/Redis）

**Files:**
- Create: `backend/app/collectors/aliyun.py`
- Create: `backend/tests/test_collectors_aliyun.py`

- [ ] **Step 1: 写失败测试（模块和类不存在）**

```python
# backend/tests/test_collectors_aliyun.py
import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_aliyun_collect_hosts_maps_metrics():
    from app.collectors.aliyun import AliyunCollector

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
    assert hosts[0].cpu_usage_percent == 81.2


@pytest.mark.asyncio
async def test_aliyun_collect_hosts_returns_empty_on_error():
    from app.collectors.aliyun import AliyunCollector

    collector = AliyunCollector("ak", "sk", "cn-hangzhou")
    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs:
        mock_ecs.side_effect = Exception("sdk error")
        hosts = await collector.collect_hosts()

    assert hosts == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_collectors_aliyun.py -v`

Expected: `ModuleNotFoundError: No module named 'app.collectors.aliyun'`

- [ ] **Step 3: 实现 AliyunCollector 最小可用代码**

```python
# backend/app/collectors/aliyun.py
import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class AliyunCollector(BaseCollector):
    def __init__(self, access_key_id: str | None, access_key_secret: str | None, region: str):
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.region = region

    async def _fetch_ecs_instances(self) -> list[dict]:
        # Phase 2 MVP: SDK 调用在后续小步补全，这里先给可mock接口
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
            logger.error("AliyunCollector.collect_hosts failed: %s", e)
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
        # Phase 2 MVP: 先保持空实现，后续小步扩展 RDS/Redis 指标
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        return []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_collectors_aliyun.py -v`

Expected:
```
tests/test_collectors_aliyun.py::test_aliyun_collect_hosts_maps_metrics PASSED
tests/test_collectors_aliyun.py::test_aliyun_collect_hosts_returns_empty_on_error PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/collectors/aliyun.py backend/tests/test_collectors_aliyun.py
git commit -m "feat: add aliyun collector host metric mapping"
```

---

## Task 3: 实现 TencentCollector（CVM/TencentDB）

**Files:**
- Create: `backend/app/collectors/tencent.py`
- Create: `backend/tests/test_collectors_tencent.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_collectors_tencent.py
import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_tencent_collect_hosts_maps_metrics():
    from app.collectors.tencent import TencentCollector

    collector = TencentCollector("sid", "skey", "ap-guangzhou")

    with patch.object(collector, "_fetch_cvm_instances", new_callable=AsyncMock) as mock_cvm, \
         patch.object(collector, "_fetch_cvm_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_cvm.return_value = [{"instance_id": "ins-001", "name": "cvm-1"}]
        mock_cpu.return_value = {"ins-001": 66.6}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "ins-001"
    assert hosts[0].cloud_provider == "tencent"
    assert hosts[0].cpu_usage_percent == 66.6


@pytest.mark.asyncio
async def test_tencent_collect_hosts_returns_empty_on_error():
    from app.collectors.tencent import TencentCollector

    collector = TencentCollector("sid", "skey", "ap-guangzhou")
    with patch.object(collector, "_fetch_cvm_instances", new_callable=AsyncMock) as mock_cvm:
        mock_cvm.side_effect = Exception("api timeout")
        hosts = await collector.collect_hosts()

    assert hosts == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_collectors_tencent.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 TencentCollector 最小代码**

```python
# backend/app/collectors/tencent.py
import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class TencentCollector(BaseCollector):
    def __init__(self, secret_id: str | None, secret_key: str | None, region: str):
        self.secret_id = secret_id
        self.secret_key = secret_key
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
            logger.error("TencentCollector.collect_hosts failed: %s", e)
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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_collectors_tencent.py -v`

Expected:
```
tests/test_collectors_tencent.py::test_tencent_collect_hosts_maps_metrics PASSED
tests/test_collectors_tencent.py::test_tencent_collect_hosts_returns_empty_on_error PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/collectors/tencent.py backend/tests/test_collectors_tencent.py
git commit -m "feat: add tencent collector host metric mapping"
```

---

## Task 4: 实现 HuaweiCollector（ECS/RDS）

**Files:**
- Create: `backend/app/collectors/huawei.py`
- Create: `backend/tests/test_collectors_huawei.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_collectors_huawei.py
import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.base import HostMetric


@pytest.mark.asyncio
async def test_huawei_collect_hosts_maps_metrics():
    from app.collectors.huawei import HuaweiCollector

    collector = HuaweiCollector("ak", "sk", "cn-north-4")

    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs, \
         patch.object(collector, "_fetch_ecs_cpu", new_callable=AsyncMock) as mock_cpu:
        mock_ecs.return_value = [{"instance_id": "hw-001", "name": "ecs-hw-1"}]
        mock_cpu.return_value = {"hw-001": 55.0}

        hosts = await collector.collect_hosts()

    assert len(hosts) == 1
    assert isinstance(hosts[0], HostMetric)
    assert hosts[0].resource_id == "hw-001"
    assert hosts[0].cloud_provider == "huawei"


@pytest.mark.asyncio
async def test_huawei_collect_hosts_returns_empty_on_error():
    from app.collectors.huawei import HuaweiCollector

    collector = HuaweiCollector("ak", "sk", "cn-north-4")
    with patch.object(collector, "_fetch_ecs_instances", new_callable=AsyncMock) as mock_ecs:
        mock_ecs.side_effect = Exception("auth failed")
        hosts = await collector.collect_hosts()

    assert hosts == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_collectors_huawei.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 HuaweiCollector 最小代码**

```python
# backend/app/collectors/huawei.py
import logging
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric

logger = logging.getLogger(__name__)


class HuaweiCollector(BaseCollector):
    def __init__(self, ak: str | None, sk: str | None, region: str):
        self.ak = ak
        self.sk = sk
        self.region = region

    async def _fetch_ecs_instances(self) -> list[dict]:
        return []

    async def _fetch_ecs_cpu(self) -> dict[str, float]:
        return {}

    async def collect_hosts(self) -> list[HostMetric]:
        try:
            instances = await self._fetch_ecs_instances()
            cpu_map = await self._fetch_ecs_cpu()
        except Exception as e:
            logger.error("HuaweiCollector.collect_hosts failed: %s", e)
            return []

        metrics: list[HostMetric] = []
        for item in instances:
            instance_id = item["instance_id"]
            metrics.append(
                HostMetric(
                    resource_id=instance_id,
                    resource_name=item.get("name", instance_id),
                    cloud_provider="huawei",
                    region=self.region,
                    cpu_usage_percent=cpu_map.get(instance_id),
                )
            )
        return metrics

    async def collect_databases(self) -> list[DBMetric]:
        return []

    async def collect_containers(self) -> list[ContainerMetric]:
        return []
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_collectors_huawei.py -v`

Expected:
```
tests/test_collectors_huawei.py::test_huawei_collect_hosts_maps_metrics PASSED
tests/test_collectors_huawei.py::test_huawei_collect_hosts_returns_empty_on_error PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/collectors/huawei.py backend/tests/test_collectors_huawei.py
git commit -m "feat: add huawei collector host metric mapping"
```

---

## Task 5: 实现 K8sCollector（Pod/Node）

**Files:**
- Create: `backend/app/collectors/k8s.py`
- Create: `backend/tests/test_collectors_k8s.py`

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_collectors_k8s.py
import pytest
from unittest.mock import AsyncMock, patch
from app.collectors.base import ContainerMetric


@pytest.mark.asyncio
async def test_k8s_collect_containers_maps_metrics():
    from app.collectors.k8s import K8sCollector

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
    assert containers[0].cloud_provider == "k8s"


@pytest.mark.asyncio
async def test_k8s_collect_containers_returns_empty_on_error():
    from app.collectors.k8s import K8sCollector

    collector = K8sCollector(config_mode="kubeconfig", kubeconfig_path=None)
    with patch.object(collector, "_fetch_pods", new_callable=AsyncMock) as mock_pods:
        mock_pods.side_effect = Exception("k8s api unavailable")
        containers = await collector.collect_containers()

    assert containers == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_collectors_k8s.py -v`

Expected: `ModuleNotFoundError`

- [ ] **Step 3: 实现 K8sCollector 最小代码**

```python
# backend/app/collectors/k8s.py
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
        except Exception as e:
            logger.error("K8sCollector.collect_containers failed: %s", e)
            return []

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
```

- [ ] **Step 4: 运行测试确认通过**

Run: `pytest tests/test_collectors_k8s.py -v`

Expected:
```
tests/test_collectors_k8s.py::test_k8s_collect_containers_maps_metrics PASSED
tests/test_collectors_k8s.py::test_k8s_collect_containers_returns_empty_on_error PASSED
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/collectors/k8s.py backend/tests/test_collectors_k8s.py
git commit -m "feat: add k8s collector container metric mapping"
```

---

## Task 6: 汇总导出采集器并接入 inspection_task

**Files:**
- Modify: `backend/app/collectors/__init__.py`
- Modify: `backend/app/tasks/inspection_task.py`
- Create: `backend/tests/test_inspection_task_multi_collectors.py`

- [ ] **Step 1: 写失败测试（尚未调用多采集器）**

```python
# backend/tests/test_inspection_task_multi_collectors.py
import pytest
from unittest.mock import AsyncMock, patch
from app.tasks.inspection_task import run_inspection_sync


@pytest.mark.asyncio
async def test_run_inspection_uses_all_collectors(db):
    with patch("app.tasks.inspection_task.PrometheusCollector") as MockProm, \
         patch("app.tasks.inspection_task.AliyunCollector") as MockAliyun, \
         patch("app.tasks.inspection_task.TencentCollector") as MockTencent, \
         patch("app.tasks.inspection_task.HuaweiCollector") as MockHuawei, \
         patch("app.tasks.inspection_task.K8sCollector") as MockK8s:

        for cls in [MockProm, MockAliyun, MockTencent, MockHuawei, MockK8s]:
            inst = cls.return_value
            inst.collect_hosts = AsyncMock(return_value=[])
            inst.collect_databases = AsyncMock(return_value=[])
            inst.collect_containers = AsyncMock(return_value=[])

        await run_inspection_sync(db=db, trigger_type="manual", trigger_user_id=None)

    assert MockAliyun.called
    assert MockTencent.called
    assert MockHuawei.called
    assert MockK8s.called
```

- [ ] **Step 2: 运行测试确认失败**

Run: `pytest tests/test_inspection_task_multi_collectors.py -v`

Expected: patch 目标不存在或断言失败

- [ ] **Step 3: 更新 collectors/__init__.py 导出新采集器**

```python
from app.collectors.base import BaseCollector, HostMetric, DBMetric, ContainerMetric
from app.collectors.prometheus import PrometheusCollector
from app.collectors.aliyun import AliyunCollector
from app.collectors.tencent import TencentCollector
from app.collectors.huawei import HuaweiCollector
from app.collectors.k8s import K8sCollector

__all__ = [
    "BaseCollector",
    "HostMetric",
    "DBMetric",
    "ContainerMetric",
    "PrometheusCollector",
    "AliyunCollector",
    "TencentCollector",
    "HuaweiCollector",
    "K8sCollector",
]
```

- [ ] **Step 4: 修改 inspection_task.py 集成全部采集器并发采集**

在 `backend/app/tasks/inspection_task.py` 中：

```python
import asyncio
# ... existing imports
from app.collectors.prometheus import PrometheusCollector
from app.collectors.aliyun import AliyunCollector
from app.collectors.tencent import TencentCollector
from app.collectors.huawei import HuaweiCollector
from app.collectors.k8s import K8sCollector


async def run_inspection_sync(db, trigger_type: str, trigger_user_id: int | None) -> str:
    # ... existing init code

    try:
        collectors = [
            PrometheusCollector(url=settings.prometheus_url),
            AliyunCollector(
                access_key_id=settings.aliyun_access_key_id,
                access_key_secret=settings.aliyun_access_key_secret,
                region=settings.aliyun_region,
            ),
            TencentCollector(
                secret_id=settings.tencent_secret_id,
                secret_key=settings.tencent_secret_key,
                region=settings.tencent_region,
            ),
            HuaweiCollector(
                ak=settings.huawei_ak,
                sk=settings.huawei_sk,
                region=settings.huawei_region,
            ),
            K8sCollector(
                config_mode=settings.k8s_config_mode,
                kubeconfig_path=settings.k8s_kubeconfig_path,
            ),
        ]

        async def collect_one(collector):
            hosts, dbs, containers = await asyncio.gather(
                collector.collect_hosts(),
                collector.collect_databases(),
                collector.collect_containers(),
            )
            return hosts, dbs, containers

        all_results = await asyncio.gather(*(collect_one(c) for c in collectors), return_exceptions=True)

        host_metrics = []
        db_metrics = []
        container_metrics = []
        for result in all_results:
            if isinstance(result, Exception):
                logger.error("Collector failed: %s", result)
                continue
            hosts, dbs, containers = result
            host_metrics.extend(hosts)
            db_metrics.extend(dbs)
            container_metrics.extend(containers)

        # 后续规则匹配逻辑保持不变
        # ...
```

- [ ] **Step 5: 运行测试确认通过**

Run:
- `pytest tests/test_inspection_task_multi_collectors.py -v`
- `pytest tests/test_inspection_task.py -v`

Expected: 全部 PASSED

- [ ] **Step 6: Commit**

```bash
git add backend/app/collectors/__init__.py backend/app/tasks/inspection_task.py backend/tests/test_inspection_task_multi_collectors.py
git commit -m "feat: integrate aliyun tencent huawei k8s collectors into inspection task"
```

---

## Task 7: 全量验证与自检

**Files:**
- Modify: `backend/app/collectors/aliyun.py`（如需修复）
- Modify: `backend/app/collectors/tencent.py`（如需修复）
- Modify: `backend/app/collectors/huawei.py`（如需修复）
- Modify: `backend/app/collectors/k8s.py`（如需修复）

- [ ] **Step 1: 运行采集器与巡检相关测试**

Run:
```bash
pytest tests/test_cloud_config.py \
       tests/test_collectors_aliyun.py \
       tests/test_collectors_tencent.py \
       tests/test_collectors_huawei.py \
       tests/test_collectors_k8s.py \
       tests/test_inspection_task.py \
       tests/test_inspection_task_multi_collectors.py -v
```

Expected: 全部 PASSED，无 FAILED

- [ ] **Step 2: 运行完整测试套件**

Run: `pytest tests/ -v`

Expected: 全部 PASSED

- [ ] **Step 3: 最终 Commit**

```bash
git add backend/app/collectors/ backend/app/tasks/inspection_task.py backend/tests/ backend/app/config.py backend/.env.example backend/requirements.txt
git commit -m "feat: implement phase2 multi-cloud and k8s collectors"
```

---

## 自审核查

**Spec 覆盖对照：**
- ✅ AliyunCollector（ECS 基础指标采集接口与映射）
- ✅ TencentCollector（CVM 基础指标采集接口与映射）
- ✅ HuaweiCollector（ECS 基础指标采集接口与映射）
- ✅ K8sCollector（Pod/容器状态采集接口与映射）
- ✅ 巡检任务并发整合多采集器
- ✅ 配置项与环境变量扩展
- ✅ 单元测试覆盖多采集器主路径与异常路径
- ⏭ 真实云 API 调用细节（可在 Phase 2.1 继续细化）
- ⏭ 云数据库深度指标（RDS/Redis/Mongo 细化）

**已知约束：**
- 本计划先确保统一接口、并发编排、可测试性与稳定错误处理。
- 真实云 API 参数、限流重试、分页拉取建议作为后续增量任务，不阻塞当前 Phase 2 主流程交付。
