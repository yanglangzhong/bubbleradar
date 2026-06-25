"""评分模型：指标归一化、分类加权、综合评分."""
from typing import Dict, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Indicator, IndicatorSnapshot


CATEGORY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "ai": {
        "ai_pe_premium": 0.25,
        "ai_funding": 0.25,
        "ai_compute": 0.20,
        "ai_sentiment": 0.20,
        "ai_vix": 0.10,
    },
    "china": {
        "housing": 0.10,
        "debt": 0.10,
        "bank": 0.07,
        "fx": 0.07,
        "real_economy": 0.07,
        "capital_market": 0.09,
        "china_equity": 0.09,
        "china_tech": 0.09,
        "china_internet": 0.09,
        "china_credit": 0.05,
        "china_fx": 0.05,
        "second_hand_listing": 0.10,
        "land_auction_premium": 0.10,
    },
    "global": {
        "us_yield_curve": 0.15,
        "credit_spread": 0.15,
        "dxy_strength": 0.12,
        "em_fx_stress": 0.12,
        "commodity_stress": 0.12,
        "global_risk_proxy": 0.12,
        "global_europe": 0.10,
        "global_japan": 0.07,
        "global_india": 0.05,
    },
    "crypto": {
        "crypto_btc": 0.30,
        "crypto_eth": 0.25,
        "crypto_ai_coins": 0.25,
        "crypto_miners": 0.20,
    },
}

COMPOSITE_WEIGHTS = {
    "ai": 0.30,
    "china": 0.30,
    "global": 0.25,
    "crypto": 0.15,
}


def normalize_value(value: float, thresholds: Dict[str, float]) -> float:
    """将原始指标值映射为 0-100 的风险分（越高越危险）."""
    watch = thresholds.get("watch")
    warning = thresholds.get("warning")
    danger = thresholds.get("danger")

    # 未配置阈值时直接返回原值并截断
    if watch is None or warning is None or danger is None:
        return max(0.0, min(100.0, float(value)))

    # 安全区：0-33
    if value <= watch:
        if watch == 0:
            return 0.0
        return (value / watch) * 33.0

    # 关注区：33-66
    if value <= warning:
        if warning == watch:
            return 33.0
        return 33.0 + (value - watch) / (warning - watch) * 33.0

    # 预警区：66-100
    if value <= danger:
        if danger == warning:
            return 66.0
        return 66.0 + (value - warning) / (danger - warning) * 34.0

    # 危险区外：>100，按超额比例继续增加但截断到 100
    base = 100.0
    extra = (value - danger) / danger * 20.0
    return min(100.0, base + extra)


def get_status(value: float, thresholds: Dict[str, float]) -> str:
    danger = thresholds.get("danger", 80)
    warning = thresholds.get("warning", 60)
    watch = thresholds.get("watch", 40)
    if value >= danger:
        return "danger"
    if value >= warning:
        return "warn"
    if value >= watch:
        return "watch"
    return "safe"


async def get_latest_snapshot(session: AsyncSession, indicator_id: int) -> IndicatorSnapshot | None:
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.indicator_id == indicator_id)
        .order_by(desc(IndicatorSnapshot.timestamp))
        .limit(1)
    )
    return result.scalar_one_or_none()


async def calculate_category_score(
    session: AsyncSession, category: str
) -> float:
    """计算某个风险分类的加权得分."""
    result = await session.execute(
        select(Indicator).where(Indicator.category == category)
    )
    indicators = result.scalars().all()
    if not indicators:
        return 0.0

    weights = CATEGORY_WEIGHTS.get(category, {})
    total_weight = 0.0
    weighted_score = 0.0

    for ind in indicators:
        snap = await get_latest_snapshot(session, ind.id)
        if snap is None:
            continue
        score = normalize_value(snap.value, ind.thresholds or {})
        weight = weights.get(ind.code, 1.0)
        weighted_score += score * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0
    return round(weighted_score / total_weight, 2)


async def calculate_composite_score(session: AsyncSession) -> float:
    ai = await calculate_category_score(session, "ai")
    china = await calculate_category_score(session, "china")
    global_ = await calculate_category_score(session, "global")
    crypto = await calculate_category_score(session, "crypto")
    composite = round(
        ai * COMPOSITE_WEIGHTS["ai"]
        + china * COMPOSITE_WEIGHTS["china"]
        + global_ * COMPOSITE_WEIGHTS["global"]
        + crypto * COMPOSITE_WEIGHTS["crypto"],
        2,
    )
    return composite
