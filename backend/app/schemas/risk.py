from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel

RiskStatus = Literal["pending", "processing", "ignored", "resolved"]


class RiskItemResponse(BaseModel):
    id: int
    inspection_id: int
    resource_type: str
    resource_id: str
    resource_name: str
    cloud_provider: Optional[str]
    risk_level: str
    risk_title: str
    risk_detail: Optional[str]
    metric_value: Optional[float]
    threshold_value: Optional[float]
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class RiskStatusUpdate(BaseModel):
    status: RiskStatus


class RiskListResponse(BaseModel):
    items: list[RiskItemResponse]
    total: int
