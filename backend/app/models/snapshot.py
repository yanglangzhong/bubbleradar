from datetime import datetime
from sqlalchemy import ForeignKey, Float, Integer, DateTime, String, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class IndicatorSnapshot(Base):
    __tablename__ = "indicator_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    indicator_id: Mapped[int] = mapped_column(Integer, ForeignKey("indicators.id"), index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="normal")  # safe, watch, warn, danger
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    meta: Mapped[dict] = mapped_column(JSON, default=dict)


class CompositeScore(Base):
    __tablename__ = "composite_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ai_bubble_score: Mapped[float] = mapped_column(Float, default=0)
    china_risk_score: Mapped[float] = mapped_column(Float, default=0)
    global_risk_score: Mapped[float] = mapped_column(Float, default=0)
    crypto_risk_score: Mapped[float] = mapped_column(Float, default=0)
    composite_score: Mapped[float] = mapped_column(Float, default=0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
