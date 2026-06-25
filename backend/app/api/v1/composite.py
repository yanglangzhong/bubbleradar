from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas import CompositeScoreOut, CompositeHistoryOut
from app.services import get_latest_composite, get_composite_history, calculate_composite_score
from app.services.calculator import _resolve_composite_source
from app.core.cache import get_cache, set_cache

router = APIRouter(prefix="/composite", tags=["composite"])


@router.get("", response_model=CompositeScoreOut)
async def get_composite(session: AsyncSession = Depends(get_db)):
    cached = await get_cache("composite:latest")
    if cached:
        return cached

    score = await get_latest_composite(session)
    if not hasattr(score, "source") or not score.source:
        score.source = await _resolve_composite_source(session)
    data = CompositeScoreOut.model_validate(score)
    await set_cache("composite:latest", data.model_dump(), expire=30)
    return data


@router.get("/history", response_model=CompositeHistoryOut)
async def get_history(days: int = 30, session: AsyncSession = Depends(get_db)):
    cache_key = f"composite:history:{days}"
    cached = await get_cache(cache_key)
    if cached:
        return CompositeHistoryOut(history=cached)

    history = await get_composite_history(session, days=days)
    data = []
    for h in history:
        if not hasattr(h, "source") or not h.source:
            h.source = await _resolve_composite_source(session)
        data.append(CompositeScoreOut.model_validate(h))
    await set_cache(cache_key, [h.model_dump() for h in data], expire=300)
    return CompositeHistoryOut(history=data)


@router.post("/recalculate", response_model=CompositeScoreOut)
async def recalculate(session: AsyncSession = Depends(get_db)):
    score = await calculate_composite_score(session)
    if not hasattr(score, "source") or not score.source:
        score.source = await _resolve_composite_source(session)
    return CompositeScoreOut.model_validate(score)


@router.get("/backtest")
async def backtest_strategy(
    days: int = Query(180, ge=30, le=365),
    risk_high: float = Query(70, ge=50, le=90),
    risk_low: float = Query(40, ge=10, le=50),
    session: AsyncSession = Depends(get_db),
):
    """基于历史综合风险分数的简单风控策略回测.

    - 基准：100% 持有风险资产
    - 风控策略：风险分 > risk_high 时减仓 50%；风险分 < risk_low 时满仓
    """
    history = await get_composite_history(session, days=days)
    if len(history) < 2:
        return {"error": "历史数据不足，无法回测"}

    dates = []
    benchmark_values = []
    strategy_values = []

    # 简化模型：风险资产日收益与风险分负相关（风险越高跌得越多）
    # 实际回测应接入真实资产价格，这里用风险分代理
    initial = 100.0
    benchmark = initial
    strategy = initial

    for h in history:
        score = h.composite_score
        dates.append(h.timestamp.strftime("%Y-%m-%d"))

        # 假设风险资产日收益 = -score / 1000（风险越高，日跌越多）
        daily_return = -score / 1000

        # 基准：满仓风险资产
        benchmark *= 1 + daily_return

        # 策略：根据风险分调仓
        if score >= risk_high:
            position = 0.5
        elif score <= risk_low:
            position = 1.0
        else:
            # 在高低阈值之间线性插值
            position = 1.0 - (score - risk_low) / (risk_high - risk_low) * 0.5

        strategy *= 1 + daily_return * position

        benchmark_values.append(round(benchmark, 2))
        strategy_values.append(round(strategy, 2))

    total_benchmark = (benchmark - initial) / initial
    total_strategy = (strategy - initial) / initial

    # 计算最大回撤
    def max_drawdown(values):
        peak = values[0]
        dd = 0
        for v in values:
            if v > peak:
                peak = v
            dd = max(dd, (peak - v) / peak)
        return round(dd * 100, 2)

    return {
        "dates": dates,
        "benchmark": benchmark_values,
        "strategy": strategy_values,
        "total_return": {
            "benchmark": round(total_benchmark * 100, 2),
            "strategy": round(total_strategy * 100, 2),
        },
        "max_drawdown": {
            "benchmark": max_drawdown(benchmark_values),
            "strategy": max_drawdown(strategy_values),
        },
        "final_value": {
            "benchmark": round(benchmark, 2),
            "strategy": round(strategy, 2),
        },
        "parameters": {
            "days": days,
            "risk_high": risk_high,
            "risk_low": risk_low,
        },
    }
