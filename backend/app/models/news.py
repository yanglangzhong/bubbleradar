from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    source: Mapped[str] = mapped_column(String(64), index=True)
    url: Mapped[str] = mapped_column(String(512), nullable=True)
    summary: Mapped[str] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float] = mapped_column(Float, default=0)  # -1 ~ 1
    impact_score: Mapped[float] = mapped_column(Float, default=50)    # 0 ~ 100
    tags: Mapped[list] = mapped_column(JSON, default=list)
    published_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
