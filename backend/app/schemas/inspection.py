from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class InspectionTriggerResponse(BaseModel):
    task_id: str
    status: str


class InspectionTaskResponse(BaseModel):
    id: int
    task_id: str
    status: str
    trigger_type: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    total_resources: int
    risk_count: Optional[dict]
    created_at: datetime

    model_config = {"from_attributes": True}


class LatestInspectionResponse(BaseModel):
    task: Optional[InspectionTaskResponse]
