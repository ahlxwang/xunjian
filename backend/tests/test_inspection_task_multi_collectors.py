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


@pytest.mark.asyncio
async def test_run_inspection_continues_on_collector_failure(db):
    """单个采集器失败不影响其他采集器"""
    with patch("app.tasks.inspection_task.PrometheusCollector") as MockProm, \
         patch("app.tasks.inspection_task.AliyunCollector") as MockAliyun, \
         patch("app.tasks.inspection_task.TencentCollector") as MockTencent, \
         patch("app.tasks.inspection_task.HuaweiCollector") as MockHuawei, \
         patch("app.tasks.inspection_task.K8sCollector") as MockK8s:

        # AliyunCollector raises an exception
        aliyun_inst = MockAliyun.return_value
        aliyun_inst.collect_hosts = AsyncMock(side_effect=Exception("Aliyun API error"))
        aliyun_inst.collect_databases = AsyncMock(return_value=[])
        aliyun_inst.collect_containers = AsyncMock(return_value=[])

        for cls in [MockProm, MockTencent, MockHuawei, MockK8s]:
            inst = cls.return_value
            inst.collect_hosts = AsyncMock(return_value=[])
            inst.collect_databases = AsyncMock(return_value=[])
            inst.collect_containers = AsyncMock(return_value=[])

        # Should complete without raising
        task_id = await run_inspection_sync(db=db, trigger_type="manual", trigger_user_id=None)

    assert task_id is not None
    assert MockTencent.called
    assert MockHuawei.called
    assert MockK8s.called


@pytest.mark.asyncio
async def test_run_inspection_aggregates_multiple_collectors(db):
    """验证多个采集器的数据正确聚合"""
    from app.models.metric import HostMetric

    with patch("app.tasks.inspection_task.PrometheusCollector") as MockProm, \
         patch("app.tasks.inspection_task.AliyunCollector") as MockAliyun, \
         patch("app.tasks.inspection_task.TencentCollector") as MockTencent, \
         patch("app.tasks.inspection_task.HuaweiCollector") as MockHuawei, \
         patch("app.tasks.inspection_task.K8sCollector") as MockK8s:

        # Prometheus 返回 2 个主机指标
        prom_inst = MockProm.return_value
        prom_inst.collect_hosts = AsyncMock(return_value=[
            HostMetric(resource_id="prom-host-1", resource_name="prom-1", cloud_provider="prometheus", region="local", cpu_usage=50.0),
            HostMetric(resource_id="prom-host-2", resource_name="prom-2", cloud_provider="prometheus", region="local", cpu_usage=60.0),
        ])
        prom_inst.collect_databases = AsyncMock(return_value=[])
        prom_inst.collect_containers = AsyncMock(return_value=[])

        # Aliyun 返回 1 个主机指标
        aliyun_inst = MockAliyun.return_value
        aliyun_inst.collect_hosts = AsyncMock(return_value=[
            HostMetric(resource_id="aliyun-host-1", resource_name="aliyun-1", cloud_provider="aliyun", region="cn-hangzhou", cpu_usage=70.0),
        ])
        aliyun_inst.collect_databases = AsyncMock(return_value=[])
        aliyun_inst.collect_containers = AsyncMock(return_value=[])

        # 其他采集器返回空
        for cls in [MockTencent, MockHuawei, MockK8s]:
            inst = cls.return_value
            inst.collect_hosts = AsyncMock(return_value=[])
            inst.collect_databases = AsyncMock(return_value=[])
            inst.collect_containers = AsyncMock(return_value=[])

        task_id = await run_inspection_sync(db=db, trigger_type="manual", trigger_user_id=None)

    # 验证任务完成
    assert task_id is not None

    # 验证聚合结果：应该有 3 个主机资源
    from sqlalchemy import select
    from app.models.inspection import InspectionTask
    result = await db.execute(select(InspectionTask).where(InspectionTask.task_id == task_id))
    inspection = result.scalar_one()
    assert inspection.total_resources == 3
    assert inspection.status == "completed"
