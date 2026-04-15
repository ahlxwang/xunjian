from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RiskItem(Base):
    __tablename__ = "risk_items"
    __table_args__ = (
        Index("idx_risk_inspection", "inspection_id"),
        Index("idx_risk_status", "status"),
        Index("idx_risk_level", "risk_level"),
        Index("idx_risk_created", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspection_tasks.id"), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cloud_provider: Mapped[str | None] = mapped_column(String(20))  # aliyun/tencent/huawei/idc
    region: Mapped[str | None] = mapped_column(String(64))
    rule_id: Mapped[int | None] = mapped_column(ForeignKey("rules.id"))
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_title: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_detail: Mapped[str | None] = mapped_column(Text)
    metric_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())


class RiskItemArchive(Base):
    """30天前的风险项归档表，结构与 RiskItem 相同，不做实时查询"""
    __tablename__ = "risk_items_archive"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_type: Mapped[str] = mapped_column(String(20), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_name: Mapped[str] = mapped_column(String(256), nullable=False)
    cloud_provider: Mapped[str | None] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(64))
    rule_id: Mapped[int | None] = mapped_column(Integer)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_title: Mapped[str] = mapped_column(String(512), nullable=False)
    risk_detail: Mapped[str | None] = mapped_column(Text)
    metric_value: Mapped[float | None] = mapped_column(Float)
    threshold_value: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    assigned_to: Mapped[int | None] = mapped_column(Integer)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    updated_at: Mapped[datetime] = mapped_column(DateTime)
    archived_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
