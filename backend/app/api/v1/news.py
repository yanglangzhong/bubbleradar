from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models import NewsArticle

router = APIRouter(prefix="/news", tags=["news"])


class NewsItem(BaseModel):
    time: str
    tag: str
    impact: str
    msg: str
    source: str
    url: str | None = None


@router.get("", response_model=List[NewsItem])
async def get_news(limit: int = 10, session: AsyncSession = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=7)
    result = await session.execute(
        select(NewsArticle)
        .where(NewsArticle.published_at >= since)
        .order_by(desc(NewsArticle.published_at))
        .limit(limit)
    )
    articles = result.scalars().all()

    items = []
    for article in articles:
        if article.impact_score >= 60:
            impact = "impact-high"
            tag = "high"
        elif article.impact_score >= 35:
            impact = "impact-mid"
            tag = "mid"
        else:
            impact = "impact-low"
            tag = "low"

        time_str = article.published_at.strftime("%H:%M") if isinstance(article.published_at, datetime) else "--"
        items.append({
            "time": time_str,
            "tag": tag,
            "impact": impact,
            "msg": article.title,
            "source": article.source or "RSS",
            "url": article.url,
        })

    # 如果数据库中无新闻，不再返回硬编码演示数据，而是返回空列表
    # 前端会据此显示"暂无实时新闻"提示
    return items[:limit]


@router.get("/sentiment")
async def news_sentiment(session: AsyncSession = Depends(get_db)):
    """返回最近24小时新闻情绪聚合."""
    since = datetime.utcnow() - timedelta(hours=24)
    result = await session.execute(
        select(
            func.avg(NewsArticle.sentiment_score).label("avg_sentiment"),
            func.avg(NewsArticle.impact_score).label("avg_impact"),
            func.count().label("count"),
        ).where(NewsArticle.published_at >= since)
    )
    row = result.one_or_none()
    return {
        "avg_sentiment": round(float(row.avg_sentiment or 0), 3),
        "avg_impact": round(float(row.avg_impact or 50), 2),
        "count": int(row.count or 0),
    }


@router.get("/signals/top")
async def top_signals(session: AsyncSession = Depends(get_db)):
    """返回当前最突出的3个风险信号（基于真实指标数据）.

    当真实数据不足时，返回空对象，前端显示"暂无信号"。
    """
    from sqlalchemy import select, desc, func
    from datetime import timedelta

    since = datetime.utcnow() - timedelta(days=1)
    result = await session.execute(
        select(
            NewsArticle.title,
            NewsArticle.source,
            NewsArticle.impact_score,
            NewsArticle.sentiment_score,
        )
        .where(NewsArticle.published_at >= since)
        .where(NewsArticle.impact_score >= 50)
        .order_by(desc(NewsArticle.impact_score))
        .limit(3)
    )
    rows = result.all()

    if not rows:
        return {
            "ai": None,
            "china": None,
            "global": None,
        }

    out = {"ai": None, "china": None, "global": None}
    keys = ["ai", "china", "global"]
    for idx, row in enumerate(rows[:3]):
        key = keys[idx] if idx < 3 else "ai"
        out[key] = {
            "title": row.title,
            "content": f"影响力评分 {row.impact_score:.0f} | 情绪 {row.sentiment_score:+.2f}",
            "history": "",
            "source": row.source or "RSS",
        }
    return out
