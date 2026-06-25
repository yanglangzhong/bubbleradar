from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models import Indicator, IndicatorSnapshot
from app.schemas import IndicatorSnapshotOut, IndicatorWithValueOut
from app.services.calculator import _label_source
from app.core.cache import get_cache, set_cache


# 指标 -> 原始数据验证链接（按数据源和内部 code 映射）
_SOURCE_URL_TEMPLATES = {
    ("fred", "us_10y"): "https://fred.stlouisfed.org/series/DGS10",
    ("fred", "us_2y"): "https://fred.stlouisfed.org/series/DGS2",
    ("fred", "us_yield_curve"): "https://fred.stlouisfed.org/series/DGS10",
    ("fred", "credit_spread"): "https://fred.stlouisfed.org/series/BAMLC0A0CM",
    ("fred", "vix"): "https://fred.stlouisfed.org/series/VIXCLS",
    ("fred", "ai_vix"): "https://fred.stlouisfed.org/series/VIXCLS",
    ("fred", "dxy"): "https://fred.stlouisfed.org/series/DTWEXBGS",
    ("fred", "dxy_strength"): "https://fred.stlouisfed.org/series/DTWEXBGS",
    ("fred", "ai_sentiment"): "https://fred.stlouisfed.org/series/NASDAQCOM",
    ("fred", "ai_pe_premium"): "https://fred.stlouisfed.org/series/SP500",
    ("alphavantage", "fx"): "https://www.alphavantage.co/query?function=FX_DAILY&from_symbol=USD&to_symbol=CNY",
    ("alphavantage", "ai_sentiment"): "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=NVDA",
    ("yahoo", "ai_pe_premium"): "https://finance.yahoo.com/quote/SOXX",
    ("yahoo", "ai_sentiment"): "https://finance.yahoo.com/quote/%5EIXIC",
    ("yahoo", "ai_compute"): "https://finance.yahoo.com/quote/SMH",
    ("yahoo", "ai_vix"): "https://finance.yahoo.com/quote/%5EVIX",
    ("yahoo", "ai_funding"): "https://finance.yahoo.com/quote/BOTZ",
    ("yahoo", "capital_market"): "https://finance.yahoo.com/quote/000300.SS",
    ("yahoo", "china_equity"): "https://finance.yahoo.com/quote/000300.SS",
    ("yahoo", "china_tech"): "https://finance.yahoo.com/quote/%5EHSTECH",
    ("yahoo", "china_internet"): "https://finance.yahoo.com/quote/KWEB",
    ("yahoo", "fx"): "https://finance.yahoo.com/quote/CNY%3DX",
    ("yahoo", "dxy_strength"): "https://finance.yahoo.com/quote/DX-Y.NYB",
    ("yahoo", "em_fx_stress"): "https://finance.yahoo.com/quote/EEM",
    ("yahoo", "commodity_stress"): "https://finance.yahoo.com/quote/DBC",
    ("yahoo", "global_europe"): "https://finance.yahoo.com/quote/%5ESTOXX50E",
    ("yahoo", "global_japan"): "https://finance.yahoo.com/quote/%5EN225",
    ("yahoo", "global_india"): "https://finance.yahoo.com/quote/%5ENSEI",
    ("yahoo", "second_hand_listing"): "https://finance.yahoo.com/quote/CHIR",
    ("eastmoney", "land_auction_premium"): "https://data.eastmoney.com/cjsj/hyzs_EMI00120219.html",
    ("akshare", "china_equity"): "http://quote.eastmoney.com/sh000300.html",
    ("akshare", "capital_market"): "http://quote.eastmoney.com/sh000300.html",
    ("akshare", "china_credit"): "https://data.eastmoney.com/cjsj/zgsgyhdzz.html",
    ("akshare", "china_fx"): "https://data.eastmoney.com/cjsj/huilv.html",
    ("akshare", "housing"): "https://www.stats.gov.cn/sj/zxfb/",
    ("akshare", "real_economy"): "https://www.stats.gov.cn/sj/zxfb/",
    ("akshare", "debt"): "http://www.mof.gov.cn/zhengwuxinxi/caizhengxinwen/",
    ("akshare", "bank"): "http://www.pbc.gov.cn/zhengcehuobisi/11140/index.html",
    ("alphavantage", "global_risk_proxy"): "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=SPY",
    ("alphavantage", "china_internet"): "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=KWEB",
    ("alphavantage", "ai_compute"): "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TSM",
    ("yahoo", "crypto_btc"): "https://finance.yahoo.com/quote/BTC-USD",
    ("yahoo", "crypto_eth"): "https://finance.yahoo.com/quote/ETH-USD",
    ("yahoo", "crypto_ai_coins"): "https://finance.yahoo.com/quote/NEAR-USD",
    ("yahoo", "crypto_miners"): "https://finance.yahoo.com/quote/MSTR",
}


def _source_url(code: str, raw_source: str) -> Optional[str]:
    """返回指标原始数据的可验证链接."""
    if not raw_source:
        return None
    key = (raw_source, code)
    return _SOURCE_URL_TEMPLATES.get(key)

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/category/{category}", response_model=List[IndicatorWithValueOut])
async def list_indicators(
    category: str,
    sub_category: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    cache_key = f"indicators:{category}:{sub_category or 'all'}"
    cached = await get_cache(cache_key)
    if cached:
        return cached

    stmt = select(Indicator).where(Indicator.category == category)
    if sub_category:
        stmt = stmt.where(Indicator.sub_category == sub_category)

    result = await session.execute(stmt)
    indicators = result.scalars().all()

    out = []
    for ind in indicators:
        snap_result = await session.execute(
            select(IndicatorSnapshot)
            .where(IndicatorSnapshot.indicator_id == ind.id)
            .order_by(desc(IndicatorSnapshot.timestamp))
            .limit(1)
        )
        snap = snap_result.scalar_one_or_none()
        raw_source = ""
        if snap and isinstance(snap.meta, dict):
            raw_source = snap.meta.get("source") or ""
        source_label = _label_source(raw_source)
        out.append(
            IndicatorWithValueOut(
                id=ind.id,
                code=ind.code,
                name_cn=ind.name_cn,
                name_en=ind.name_en,
                category=ind.category,
                sub_category=ind.sub_category,
                unit=ind.unit,
                update_frequency=ind.update_frequency,
                description=ind.description,
                thresholds=ind.thresholds,
                is_simulated=ind.is_simulated,
                created_at=ind.created_at,
                latest_value=snap.value if snap else None,
                latest_status=snap.status if snap else None,
                latest_timestamp=snap.timestamp if snap else None,
                source=source_label,
                source_url=_source_url(ind.code, raw_source),
            )
        )

    await set_cache(cache_key, [item.model_dump() for item in out], expire=30)
    return out


@router.get("/{indicator_id}/history", response_model=List[IndicatorSnapshotOut])
async def indicator_history(
    indicator_id: int,
    limit: int = Query(90, ge=1, le=1000),
    session: AsyncSession = Depends(get_db),
):
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(IndicatorSnapshot.indicator_id == indicator_id)
        .order_by(desc(IndicatorSnapshot.timestamp))
        .limit(limit)
    )
    return list(result.scalars().all())


_STATUS_TO_INT = {"safe": 0, "watch": 1, "warn": 2, "danger": 3}


@router.get("/heatmap")
async def indicators_heatmap(
    days: int = Query(30, ge=7, le=365),
    session: AsyncSession = Depends(get_db),
):
    """返回时间 × 指标的风险热力图数据."""
    since = datetime.utcnow() - timedelta(days=days)

    result = await session.execute(
        select(Indicator).order_by(Indicator.category, Indicator.sub_category, Indicator.code)
    )
    indicators = result.scalars().all()
    indicator_list = [
        {"id": ind.id, "code": ind.code, "name_cn": ind.name_cn, "category": ind.category}
        for ind in indicators
    ]

    # 按天聚合每个指标的最新状态
    date_labels = []
    date_to_idx = {}
    for i in range(days, -1, -1):
        d = (datetime.utcnow() - timedelta(days=i)).strftime("%Y-%m-%d")
        date_labels.append(d)
        date_to_idx[d] = len(date_labels) - 1

    # 初始化矩阵：行=指标，列=日期，无数据为 null
    matrix = [[None] * len(date_labels) for _ in indicators]

    for row_idx, ind in enumerate(indicators):
        snaps = await session.execute(
            select(IndicatorSnapshot)
            .where(
                IndicatorSnapshot.indicator_id == ind.id,
                IndicatorSnapshot.timestamp >= since,
            )
            .order_by(desc(IndicatorSnapshot.timestamp))
        )
        for snap in snaps.scalars().all():
            d = snap.timestamp.strftime("%Y-%m-%d")
            if d in date_to_idx:
                col_idx = date_to_idx[d]
                if matrix[row_idx][col_idx] is None:
                    matrix[row_idx][col_idx] = _STATUS_TO_INT.get(snap.status, 0)

    return {
        "dates": date_labels,
        "indicators": indicator_list,
        "matrix": matrix,
    }
