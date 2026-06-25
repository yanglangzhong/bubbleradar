"""Aggregated dashboard endpoint - returns all data the Dashboard needs in one call."""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cache, set_cache
from app.db.session import get_db
from app.models import NewsArticle
from app.schemas import CompositeScoreOut, IndicatorWithValueOut
from app.services import get_latest_composite, get_composite_history, get_indicators_by_category
from app.services.calculator import _resolve_composite_source

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

CACHE_KEY = "dashboard:aggregated"
CACHE_TTL = 15  # seconds


class DashboardSignals(BaseModel):
    ai: Optional[dict] = None
    china: Optional[dict] = None
    global_: Optional[dict] = Field(default=None, serialization_alias="global")


class AnalysisStatusOut(BaseModel):
    status: str
    message: str


class DashboardData(BaseModel):
    composite: Optional[dict] = None
    history: List[dict] = []
    ai_indicators: List[dict] = []
    china_indicators: List[dict] = []
    news: List[dict] = []
    signals: Optional[DashboardSignals] = None
    analysis_status: AnalysisStatusOut = AnalysisStatusOut(status="pending", message="")


def _serialize_composite(score) -> dict:
    """Serialize a CompositeScore ORM object to dict, resolving source if needed."""
    return {
        "ai_bubble_score": score.ai_bubble_score,
        "china_risk_score": score.china_risk_score,
        "global_risk_score": score.global_risk_score,
        "crypto_risk_score": score.crypto_risk_score,
        "composite_score": score.composite_score,
        "timestamp": score.timestamp.isoformat() if score.timestamp else None,
        "source": getattr(score, "source", None) or "历史记录",
    }


async def _fetch_composite(session: AsyncSession) -> Optional[dict]:
    try:
        score = await get_latest_composite(session)
        if not hasattr(score, "source") or not score.source:
            score.source = await _resolve_composite_source(session)
        return _serialize_composite(score)
    except Exception as exc:
        logger.warning("dashboard: composite fetch failed: %s", exc)
        return None


async def _fetch_history(session: AsyncSession) -> List[dict]:
    try:
        history = await get_composite_history(session, days=7)
        result = []
        for h in history:
            if not hasattr(h, "source") or not h.source:
                h.source = await _resolve_composite_source(session)
            result.append(_serialize_composite(h))
        return result
    except Exception as exc:
        logger.warning("dashboard: history fetch failed: %s", exc)
        return []


async def _fetch_indicators(session: AsyncSession, category: str) -> List[dict]:
    try:
        indicators = await get_indicators_by_category(session, category)
        return [IndicatorWithValueOut.model_validate(ind).model_dump() for ind in indicators]
    except Exception as exc:
        logger.warning("dashboard: indicators(%s) fetch failed: %s", category, exc)
        return []


async def _fetch_news(session: AsyncSession) -> List[dict]:
    try:
        since = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .order_by(desc(NewsArticle.published_at))
            .limit(8)
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
        return items
    except Exception as exc:
        logger.warning("dashboard: news fetch failed: %s", exc)
        return []


async def _fetch_signals(session: AsyncSession) -> dict:
    try:
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
        out: dict = {"ai": None, "china": None, "global": None}
        if not rows:
            return out
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
    except Exception as exc:
        logger.warning("dashboard: signals fetch failed: %s", exc)
        return {"ai": None, "china": None, "global": None}


async def build_dashboard_data(session: AsyncSession) -> dict:
    """构建仪表盘聚合数据字典，供 REST 与 WebSocket 共用."""
    composite = await _fetch_composite(session)
    history = await _fetch_history(session)
    ai_indicators = await _fetch_indicators(session, "ai")
    china_indicators = await _fetch_indicators(session, "china")
    news = await _fetch_news(session)
    signals = await _fetch_signals(session)

    data = DashboardData(
        composite=composite,
        history=history,
        ai_indicators=ai_indicators,
        china_indicators=china_indicators,
        news=news,
        signals=signals,
        analysis_status=AnalysisStatusOut(status="ready", message="数据已就绪"),
    )
    return data.model_dump(by_alias=True)


@router.get("", response_model=DashboardData)
async def get_dashboard_data(session: AsyncSession = Depends(get_db)):
    """Aggregated dashboard data - single call replaces 8 separate requests.

    Results are cached in Redis for 15 seconds to reduce database load.
    Each data source is fetched independently with error isolation.
    """
    # Check cache first
    cached = await get_cache(CACHE_KEY)
    if cached:
        return DashboardData(**cached)

    payload = await build_dashboard_data(session)
    data = DashboardData(**payload)

    # Cache for 15 seconds (store with field aliases so consumers see "global")
    await set_cache(CACHE_KEY, payload, expire=CACHE_TTL)

    return data
