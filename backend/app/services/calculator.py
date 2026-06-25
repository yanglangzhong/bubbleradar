from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import Counter
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Indicator, IndicatorSnapshot, CompositeScore
from app.services.scoring import calculate_category_score, get_status


SOURCE_LABELS = {
    "fred": "FRED（圣路易斯联储）",
    "yahoo": "Yahoo Finance",
    "alphavantage": "Alpha Vantage",
    "akshare": "AkShare",
    "历史基线（无新数据）": "历史基线（无新数据）",
    "历史基线推演": "历史基线（无新数据）",
    "crawler": "历史基线（无新数据）",
    "unknown": "历史基线（无新数据）",
}


def _label_source(raw: str) -> str:
    if not raw:
        return "历史基线（无新数据）"
    return SOURCE_LABELS.get(raw, raw)


async def _resolve_composite_source(session: AsyncSession) -> str:
    """统计最近 1 小时内各指标快照的数据来源，返回可读来源说明."""
    since = datetime.utcnow() - timedelta(hours=1)
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.timestamp >= since)
        .order_by(desc(IndicatorSnapshot.timestamp))
    )
    snaps = result.scalars().all()

    # 只统计有明确来源的快照；seed/历史数据不纳入来源说明
    counter: Counter = Counter()
    for snap in snaps:
        raw = ""
        if isinstance(snap.meta, dict):
            raw = snap.meta.get("source") or ""
        label = _label_source(raw)
        if label != "历史基线（无新数据）":
            counter[label] += 1

    if not counter:
        return "历史基线（无新数据）"

    top = counter.most_common(3)
    return " / ".join(f"{name} ×{cnt}" for name, cnt in top)


async def get_latest_snapshot(session: AsyncSession, indicator_id: int) -> Optional[IndicatorSnapshot]:
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.indicator_id == indicator_id)
        .order_by(desc(IndicatorSnapshot.timestamp))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def calculate_ai_bubble_score(session: AsyncSession) -> float:
    return await calculate_category_score(session, "ai")


async def calculate_china_risk_score(session: AsyncSession) -> float:
    return await calculate_category_score(session, "china")


async def calculate_global_risk_score(session: AsyncSession) -> float:
    return await calculate_category_score(session, "global")


async def calculate_crypto_risk_score(session: AsyncSession) -> float:
    return await calculate_category_score(session, "crypto")


async def calculate_composite_score(session: AsyncSession) -> CompositeScore:
    ai_score = await calculate_ai_bubble_score(session)
    china_score = await calculate_china_risk_score(session)
    global_score = await calculate_global_risk_score(session)
    crypto_score = await calculate_crypto_risk_score(session)
    composite = round(
        ai_score * 0.30 + china_score * 0.30 + global_score * 0.25 + crypto_score * 0.15,
        2,
    )

    score = CompositeScore(
        ai_bubble_score=ai_score,
        china_risk_score=china_score,
        global_risk_score=global_score,
        crypto_risk_score=crypto_score,
        composite_score=composite,
    )
    # 附加数据来源说明（非数据库字段，仅用于 API 返回）
    score.source = await _resolve_composite_source(session)
    session.add(score)
    await session.commit()
    return score


async def get_latest_composite(session: AsyncSession) -> CompositeScore:
    result = await session.execute(
        select(CompositeScore).order_by(desc(CompositeScore.timestamp)).limit(1)
    )
    score = result.scalar_one_or_none()
    if score is None:
        score = await calculate_composite_score(session)
    if not hasattr(score, "source") or not score.source:
        score.source = await _resolve_composite_source(session)
    return score


async def get_composite_history(session: AsyncSession, days: int = 30) -> List[CompositeScore]:
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(CompositeScore)
        .where(CompositeScore.timestamp >= since)
        .order_by(CompositeScore.timestamp)
    )
    return list(result.scalars().all())


async def get_indicators_by_category(
    session: AsyncSession, category: str
) -> List[dict]:
    result = await session.execute(
        select(Indicator).where(Indicator.category == category)
    )
    indicators = result.scalars().all()
    out = []
    for ind in indicators:
        snap = await get_latest_snapshot(session, ind.id)
        out.append({
            "id": ind.id,
            "code": ind.code,
            "name_cn": ind.name_cn,
            "name_en": ind.name_en,
            "category": ind.category,
            "sub_category": ind.sub_category,
            "unit": ind.unit,
            "source": ind.source,
            "is_simulated": ind.is_simulated,
            "latest_value": snap.value if snap else None,
            "latest_status": snap.status if snap else None,
            "latest_timestamp": snap.timestamp if snap else None,
        })
    return out
