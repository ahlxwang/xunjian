from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class RuleResponse(BaseModel):
    id: int
    rule_code: str
    rule_name: str
    resource_type: str
    metric_name: str
    operator: str
    threshold_value: float
    risk_level: str
    enabled: bool
    description: Optional[str]

    model_config = {"from_attributes": True}


class RuleUpdate(BaseModel):
    threshold_value: Optional[float] = None
    enabled: Optional[bool] = None
