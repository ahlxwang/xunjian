from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.risk import RiskItem
from app.schemas.risk import RiskItemResponse, RiskStatusUpdate, RiskListResponse

router = APIRouter(prefix="/api/v1/risks", tags=["risks"])


@router.get("", response_model=RiskListResponse)
async def list_risks(
    risk_level: str | None = Query(None),
    status: str | None = Query(None),
    cloud_provider: str | None = Query(None),
    resource_type: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(RiskItem)
    if risk_level:
        query = query.where(RiskItem.risk_level == risk_level)
    if status:
        query = query.where(RiskItem.status == status)
    if cloud_provider:
        query = query.where(RiskItem.cloud_provider == cloud_provider)
    if resource_type:
        query = query.where(RiskItem.resource_type == resource_type)

    # dev 角色只能看自己负责的服务
    if current_user.role == "dev" and current_user.responsible_services:
        services = current_user.responsible_services
        query = query.where(RiskItem.resource_name.in_(services))

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = result.scalars().all()

    return RiskListResponse(items=items, total=total)


@router.patch("/{risk_id}/status", response_model=RiskItemResponse)
async def update_risk_status(
    risk_id: int,
    body: RiskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskItem).where(RiskItem.id == risk_id))
    risk = result.scalar_one_or_none()
    if not risk:
        raise HTTPException(status_code=404, detail="Risk item not found")

    # dev 角色只能更新自己负责的服务的风险项
    if current_user.role == "dev" and current_user.responsible_services:
        services = current_user.responsible_services
        if risk.resource_name not in services:
            raise HTTPException(status_code=403, detail="Insufficient permissions")

    risk.status = body.status
    await db.commit()
    await db.refresh(risk)
    return risk
