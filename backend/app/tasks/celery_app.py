from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery_app = Celery(
    "inspection",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.inspection_task", "app.tasks.cleanup_task"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    beat_schedule={
        "daily-inspection": {
            "task": "app.tasks.inspection_task.run_inspection",
            "schedule": crontab(hour=8, minute=0),
            "kwargs": {"trigger_type": "scheduled"},
        },
        "cleanup-old-risks": {
            "task": "app.tasks.cleanup_task.archive_old_risks",
            "schedule": crontab(hour=2, minute=0),
        },
    },
)
