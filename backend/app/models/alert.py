from datetime import datetime
from sqlalchemy import ForeignKey, Float, Integer, DateTime, String, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    indicator_id: Mapped[int] = mapped_column(Integer, ForeignKey("indicators.id"), nullable=True)
    condition: Mapped[str] = mapped_column(String(16))  # gt, lt, eq, between
    threshold: Mapped[float] = mapped_column(Float)
    threshold_secondary: Mapped[float] = mapped_column(Float, nullable=True)  # for between
    severity: Mapped[str] = mapped_column(String(16), default="watch")  # info, watch, warn, danger
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertEvent(Base):
    __tablename__ = "alert_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    rule_id: Mapped[int] = mapped_column(Integer, ForeignKey("alert_rules.id"))
    indicator_id: Mapped[int] = mapped_column(Integer, ForeignKey("indicators.id"), nullable=True)
    value: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
