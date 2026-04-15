from datetime import datetime
from sqlalchemy import String, Float, Boolean, DateTime, Text, func, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Rule(Base):
    __tablename__ = "rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(256), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)  # host/container/database
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    operator: Mapped[str] = mapped_column(String(10), nullable=False)  # >, <, ==, !=
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)  # critical/high/medium/low
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_rule_resource_type", "resource_type"),
        Index("idx_rule_enabled", "enabled"),
    )
