from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Float, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class DataSource(Base):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(64), unique=True)
    url: Mapped[str] = mapped_column(String(256), nullable=True)
    api_type: Mapped[str] = mapped_column(String(32), default="rest")
    auth_method: Mapped[str] = mapped_column(String(32), nullable=True)
    reliability_score: Mapped[float] = mapped_column(Float, default=1.0)
    last_success: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    config: Mapped[dict] = mapped_column(JSON, default=dict)
