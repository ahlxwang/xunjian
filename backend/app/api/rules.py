from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.rule import Rule
from app.schemas.rule import RuleResponse, RuleUpdate

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


@router.get("", response_model=list[RuleResponse])
async def list_rules(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rule))
    return result.scalars().all()


@router.patch("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: int,
    body: RuleUpdate,
    _: User = Depends(require_role("admin", "ops")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    if body.threshold_value is not None:
        rule.threshold_value = body.threshold_value
    if body.enabled is not None:
        rule.enabled = body.enabled

    await db.commit()
    await db.refresh(rule)
    return rule
