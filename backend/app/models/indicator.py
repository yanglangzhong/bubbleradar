from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Indicator(Base):
    __tablename__ = "indicators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name_cn: Mapped[str] = mapped_column(String(128))
    name_en: Mapped[str] = mapped_column(String(128), nullable=True)
    category: Mapped[str] = mapped_column(String(32), index=True)  # ai, china, global
    sub_category: Mapped[str] = mapped_column(String(32), nullable=True)  # housing, debt, etc.
    unit: Mapped[str] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=True)
    update_frequency: Mapped[str] = mapped_column(String(16), default="daily")
    description: Mapped[str] = mapped_column(Text, nullable=True)
    thresholds: Mapped[dict] = mapped_column(JSON, default=dict)  # {"warning": 60, "danger": 80}
    is_simulated: Mapped[bool] = mapped_column(default=False)  # 是否为模拟/无真实数据源指标
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
