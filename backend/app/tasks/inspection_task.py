import asyncio
import uuid
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.inspection import InspectionTask
from app.models.risk import RiskItem
from app.models.rule import Rule
from app.collectors.prometheus import PrometheusCollector
from app.collectors.aliyun import AliyunCollector
from app.collectors.tencent import TencentCollector
from app.collectors.huawei import HuaweiCollector
from app.collectors.k8s import K8sCollector
from app.engine.rule_engine import RuleEngine
from app.config import settings
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)


async def run_inspection_sync(
    db: AsyncSession,
    trigger_type: str,
    trigger_user_id: int | None,
) -> str:
    """核心巡检逻辑（async），供 Celery task 和测试调用"""
    task_id = str(uuid.uuid4())
    start_time = datetime.utcnow()

    # 1. 创建巡检记录
    inspection = InspectionTask(
        task_id=task_id,
        status="running",
        trigger_type=trigger_type,
        trigger_user_id=trigger_user_id,
        start_time=start_time,
    )
    db.add(inspection)
    await db.commit()
    await db.refresh(inspection)

    try:
        # 2. 并发采集 - 使用所有采集器
        collectors = [
            PrometheusCollector(url=settings.prometheus_url),
            AliyunCollector(
                access_key_id=settings.aliyun_access_key_id,
                access_key_secret=settings.aliyun_access_key_secret.get_secret_value() if settings.aliyun_access_key_secret else None,
                region=settings.aliyun_region,
            ),
            TencentCollector(
                secret_id=settings.tencent_secret_id,
                secret_key=settings.tencent_secret_key.get_secret_value() if settings.tencent_secret_key else None,
                region=settings.tencent_region,
            ),
            HuaweiCollector(
                access_key=settings.huawei_access_key,
                secret_key=settings.huawei_secret_key.get_secret_value() if settings.huawei_secret_key else None,
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

        all_results = await asyncio.gather(
            *(collect_one(c) for c in collectors),
            return_exceptions=True
        )

        # 聚合所有采集器的结果
        host_metrics = []
        db_metrics = []
        container_metrics = []
        for idx, result in enumerate(all_results):
            if isinstance(result, Exception):
                logger.error("Collector %s failed: %s", type(collectors[idx]).__name__, str(result)[:200])
                continue
            hosts, dbs, containers = result
            host_metrics.extend(hosts)
            db_metrics.extend(dbs)
            container_metrics.extend(containers)

        # 3. 加载规则
        result = await db.execute(select(Rule).where(Rule.enabled.is_(True)))
        rules = result.scalars().all()
        engine = RuleEngine(rules)

        # 4. 规则匹配，生成风险项
        risk_items = []
        for metric in host_metrics:
            for match in engine.evaluate_host(metric):
                risk_items.append(RiskItem(
                    inspection_id=inspection.id,
                    resource_type="host",
                    resource_id=metric.resource_id,
                    resource_name=metric.resource_name,
                    cloud_provider=metric.cloud_provider,
                    region=metric.region,
                    rule_id=match.rule.id,
                    risk_level=match.risk_level,
                    risk_title=match.risk_title,
                    risk_detail=match.risk_detail,
                    metric_value=match.metric_value,
                    threshold_value=match.threshold_value,
                    status="pending",
                ))

        db.add_all(risk_items)

        # 5. 统计风险数量
        risk_count: dict[str, int] = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for item in risk_items:
            risk_count[item.risk_level] = risk_count.get(item.risk_level, 0) + 1

        # 6. 更新巡检记录
        inspection.status = "completed"
        inspection.end_time = datetime.utcnow()
        inspection.total_resources = len(host_metrics) + len(db_metrics) + len(container_metrics)
        inspection.risk_count = risk_count
        await db.commit()

    except Exception as e:
        logger.error("Inspection %s failed: %s", task_id, e)
        inspection.status = "failed"
        inspection.end_time = datetime.utcnow()
        await db.commit()

    return task_id


@celery_app.task(name="app.tasks.inspection_task.run_inspection", bind=True)
def run_inspection(self, trigger_type: str = "scheduled", trigger_user_id: int | None = None):
    async def _run():
        async with AsyncSessionLocal() as db:
            return await run_inspection_sync(db, trigger_type, trigger_user_id)
    return asyncio.run(_run())
