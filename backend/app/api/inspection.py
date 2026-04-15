from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.inspection import InspectionTask
from app.schemas.inspection import InspectionTriggerResponse, LatestInspectionResponse, InspectionTaskResponse
from app.tasks.inspection_task import run_inspection_sync

router = APIRouter(prefix="/api/v1/inspection", tags=["inspection"])


@router.post("/trigger", response_model=InspectionTriggerResponse, status_code=202)
async def trigger_inspection(
    current_user: User = Depends(require_role("admin", "ops")),
    db: AsyncSession = Depends(get_db),
):
    task_id = await run_inspection_sync(db, trigger_type="manual", trigger_user_id=current_user.id)
    return InspectionTriggerResponse(task_id=task_id, status="running")


@router.get("/latest", response_model=LatestInspectionResponse)
async def get_latest_inspection(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InspectionTask).order_by(desc(InspectionTask.created_at)).limit(1)
    )
    task = result.scalar_one_or_none()
    return LatestInspectionResponse(task=InspectionTaskResponse.model_validate(task) if task else None)


@router.get("/history", response_model=list[InspectionTaskResponse])
async def get_inspection_history(
    limit: int = 30,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(InspectionTask).order_by(desc(InspectionTask.created_at)).limit(limit)
    )
    return result.scalars().all()
