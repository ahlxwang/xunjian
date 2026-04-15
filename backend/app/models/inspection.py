from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.database import Base


class InspectionTask(Base):
    __tablename__ = "inspection_tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # pending/running/completed/failed
    trigger_type: Mapped[str] = mapped_column(String(20), nullable=False)  # manual/scheduled
    trigger_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    total_resources: Mapped[int] = mapped_column(Integer, default=0)
    risk_count: Mapped[dict | None] = mapped_column(JSONB)  # {"critical": 3, "high": 9, ...}
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_inspection_status", "status"),
        Index("idx_inspection_created", "created_at"),
    )
