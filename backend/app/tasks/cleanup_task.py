import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, delete, insert
from app.database import AsyncSessionLocal
from app.models.risk import RiskItem, RiskItemArchive
from app.models.inspection import InspectionTask
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

RETENTION_DAYS = 30


async def _archive_old_risks_async():
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    async with AsyncSessionLocal() as db:
        # 查询需要归档的记录
        result = await db.execute(
            select(RiskItem).where(RiskItem.created_at < cutoff)
        )
        old_items = result.scalars().all()

        if not old_items:
            logger.info("No risk items to archive")
            # Still clean up old inspection_tasks that have no risk_items
            await db.execute(
                delete(InspectionTask).where(
                    InspectionTask.created_at < cutoff,
                    ~InspectionTask.id.in_(select(RiskItem.inspection_id).distinct())
                )
            )
            await db.commit()
            return 0

        # 插入归档表
        archive_rows = [
            {c.key: getattr(item, c.key) for c in RiskItem.__table__.columns}
            for item in old_items
        ]
        await db.execute(insert(RiskItemArchive), archive_rows)

        # 从主表删除
        ids = [item.id for item in old_items]
        await db.execute(delete(RiskItem).where(RiskItem.id.in_(ids)))

        # 只删除已没有关联风险项的 inspection_tasks（安全地避免 FK 违反）
        await db.execute(
            delete(InspectionTask).where(
                InspectionTask.created_at < cutoff,
                ~InspectionTask.id.in_(select(RiskItem.inspection_id).distinct())
            )
        )

        await db.commit()
        logger.info("Archived %d risk items older than %d days", len(ids), RETENTION_DAYS)
        return len(ids)


@celery_app.task(name="app.tasks.cleanup_task.archive_old_risks")
def archive_old_risks():
    return asyncio.run(_archive_old_risks_async())
