"""数据分析 API：预测、相关性、危机相似度."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.analytics import (
    forecast_indicator,
    correlation_matrix,
    crisis_similarity,
    list_events,
    correlation_network,
    china_dimension_scores,
    global_linkage_series,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/indicators/{indicator_id}/forecast")
async def indicator_forecast(indicator_id: int, session: AsyncSession = Depends(get_db)):
    result = await forecast_indicator(session, indicator_id)
    if result is None:
        raise HTTPException(status_code=404, detail="历史数据不足，无法预测")
    return result


class CorrelationRequest(BaseModel):
    codes: List[str]
    days: int = 60


@router.post("/indicators/correlation")
async def indicators_correlation(
    body: CorrelationRequest, session: AsyncSession = Depends(get_db)
):
    result = await correlation_matrix(session, body.codes, days=body.days)
    if result is None:
        raise HTTPException(status_code=400, detail="指标代码无效或历史数据不足")
    return result


@router.get("/composite/similarity")
async def composite_similarity(session: AsyncSession = Depends(get_db)):
    return await crisis_similarity(session)


@router.get("/events")
async def get_events(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db),
):
    return await list_events(session, category=category, limit=limit)


@router.get("/network")
async def get_network(
    category: Optional[str] = None,
    days: int = Query(60, ge=7, le=365),
    threshold: float = Query(0.5, ge=0.0, le=1.0),
    session: AsyncSession = Depends(get_db),
):
    return await correlation_network(session, category=category, days=days, threshold=threshold)


@router.get("/china/dimensions")
async def get_china_dimensions(session: AsyncSession = Depends(get_db)):
    """中国经济六维风险雷达数据（按子类别聚合真实指标）."""
    return await china_dimension_scores(session)


@router.get("/global/linkage")
async def get_global_linkage(
    days: int = Query(30, ge=7, le=365),
    session: AsyncSession = Depends(get_db),
):
    """全球风险联动指标时间序列（中美利差、铜/油比、新兴市场货币指数）."""
    return await global_linkage_series(session, days=days)
