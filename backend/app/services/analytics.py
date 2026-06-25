"""数据分析：预测、相关性、危机相似度."""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Indicator, IndicatorSnapshot, CompositeScore, HistoricalEvent
from app.services.scoring import calculate_category_score, normalize_value


async def fetch_indicator_history(
    session: AsyncSession, indicator_id: int, days: int = 60
) -> List[tuple]:
    since = datetime.utcnow() - timedelta(days=days)
    result = await session.execute(
        select(IndicatorSnapshot)
        .where(
            IndicatorSnapshot.indicator_id == indicator_id,
            IndicatorSnapshot.timestamp >= since,
        )
        .order_by(IndicatorSnapshot.timestamp)
    )
    rows = result.scalars().all()
    return [(r.timestamp, r.value) for r in rows]


async def forecast_indicator(
    session: AsyncSession, indicator_id: int, days: int = 7
) -> Optional[Dict]:
    """基于线性回归预测未来值与趋势."""
    history = await fetch_indicator_history(session, indicator_id, days=60)
    if len(history) < 5:
        return None

    x = np.arange(len(history))
    y = np.array([v for _, v in history])
    coeffs = np.polyfit(x, y, 1)
    slope, intercept = coeffs
    next_value = slope * len(history) + intercept
    # R^2
    predictions = slope * x + intercept
    ss_res = np.sum((y - predictions) ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot else 0

    return {
        "next_value": round(float(next_value), 2),
        "slope": round(float(slope), 4),
        "trend": "up" if slope > 0 else "down" if slope < 0 else "flat",
        "r2": round(float(r2), 3),
        "history_points": len(history),
    }


async def correlation_matrix(
    session: AsyncSession, codes: List[str], days: int = 60
) -> Optional[Dict]:
    """计算多个指标历史序列的皮尔逊相关系数矩阵."""
    data: Dict[str, List[float]] = {}
    for code in codes:
        result = await session.execute(
            select(Indicator).where(Indicator.code == code)
        )
        indicator = result.scalar_one_or_none()
        if not indicator:
            continue
        history = await fetch_indicator_history(session, indicator.id, days)
        data[code] = [v for _, v in history]

    if len(data) < 2:
        return None

    # 取最短长度对齐
    min_len = min(len(v) for v in data.values())
    if min_len < 5:
        return None

    arrays = [np.array(v[-min_len:]) for v in data.values()]
    corr = np.corrcoef(arrays)

    keys = list(data.keys())
    matrix = {
        keys[i]: {
            keys[j]: round(float(corr[i][j]), 3) for j in range(len(keys))
        }
        for i in range(len(keys))
    }
    return {"codes": keys, "matrix": matrix, "points": min_len}


CRISIS_TEMPLATES = {
    "2000 Dot-com": {"ai": 85, "china": 30, "global": 55},
    "2008 GFC": {"ai": 45, "china": 40, "global": 90},
    "2015 China Shock": {"ai": 35, "china": 80, "global": 50},
    "2020 COVID Crash": {"ai": 50, "china": 55, "global": 85},
}


async def crisis_similarity(session: AsyncSession) -> Dict:
    """将当前分类得分与历史危机模板做欧氏距离相似度匹配."""
    current = {
        "ai": await calculate_category_score(session, "ai"),
        "china": await calculate_category_score(session, "china"),
        "global": await calculate_category_score(session, "global"),
    }

    results = []
    for name, template in CRISIS_TEMPLATES.items():
        dist = np.sqrt(
            sum((current[k] - template[k]) ** 2 for k in current)
        )
        # 相似度：距离越小越接近 100
        similarity = max(0, 100 - dist)
        results.append({
            "name": name,
            "similarity": round(float(similarity), 2),
            "distance": round(float(dist), 2),
            "current": current,
            "template": template,
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return {"current": current, "matches": results}


async def list_events(
    session: AsyncSession, category: Optional[str] = None, limit: int = 50
) -> List[Dict]:
    """返回历史事件列表，按日期降序."""
    stmt = select(HistoricalEvent).order_by(desc(HistoricalEvent.date))
    if category:
        stmt = stmt.where(HistoricalEvent.category == category)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "date": r.date.isoformat() if r.date else None,
            "title": r.title,
            "category": r.category,
            "description": r.description,
            "source": r.source,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


async def correlation_network(
    session: AsyncSession, category: Optional[str] = None, days: int = 60, threshold: float = 0.5
) -> Dict:
    """计算指标间相关性网络，返回节点与边."""
    stmt = select(Indicator)
    if category:
        stmt = stmt.where(Indicator.category == category)
    result = await session.execute(stmt)
    indicators = result.scalars().all()

    data: Dict[int, List[float]] = {}
    latest: Dict[int, float] = {}
    for ind in indicators:
        history = await fetch_indicator_history(session, ind.id, days)
        if len(history) >= 5:
            data[ind.id] = [v for _, v in history]
            latest[ind.id] = history[-1][1]

    if len(data) < 2:
        return {"nodes": [], "edges": []}

    min_len = min(len(v) for v in data.values())
    arrays = [np.array(v[-min_len:]) for v in data.values()]
    corr = np.corrcoef(arrays)

    ind_list = list(data.keys())
    ind_map = {ind.id: ind for ind in indicators}

    nodes = []
    for idx, ind_id in enumerate(ind_list):
        ind = ind_map[ind_id]
        nodes.append({
            "id": ind_id,
            "code": ind.code,
            "name": ind.name_cn,
            "category": ind.category,
            "value": round(float(latest[ind_id]), 2),
        })

    edges = []
    for i in range(len(ind_list)):
        for j in range(i + 1, len(ind_list)):
            value = float(corr[i][j])
            if abs(value) >= threshold:
                edges.append({
                    "source": ind_list[i],
                    "target": ind_list[j],
                    "value": round(value, 3),
                })

    return {"nodes": nodes, "edges": edges}


CHINA_DIMENSION_MAP = {
    "housing": "房地产",
    "debt": "地方债",
    "bank": "银行系统",
    "fx": "外汇资本",
    "real": "实体就业",
    "market": "资本市场",
}


async def china_dimension_scores(session: AsyncSession) -> Dict:
    """按子类别聚合中国经济指标，生成六维风险雷达数据."""
    stmt = select(Indicator).where(Indicator.category == "china")
    result = await session.execute(stmt)
    indicators = result.scalars().all()

    groups: Dict[str, List[float]] = {key: [] for key in CHINA_DIMENSION_MAP}
    for ind in indicators:
        sub = ind.sub_category or ""
        # 将部分子类别映射到六维
        if sub in ("housing",):
            key = "housing"
        elif sub in ("debt",):
            key = "debt"
        elif sub in ("bank",):
            key = "bank"
        elif sub in ("fx",):
            key = "fx"
        elif sub in ("real",):
            key = "real"
        elif sub in ("market",):
            key = "market"
        else:
            continue

        snap = await get_latest_snapshot(session, ind.id)
        if snap is not None:
            score = normalize_value(snap.value, ind.thresholds or {})
            groups[key].append(score)

    values = []
    for key, label in CHINA_DIMENSION_MAP.items():
        scores = groups[key]
        value = round(sum(scores) / len(scores), 1) if scores else 0.0
        values.append({"key": key, "label": label, "value": value})

    return {
        "labels": [v["label"] for v in values],
        "values": [v["value"] for v in values],
        "details": values,
    }


async def global_linkage_series(session: AsyncSession, days: int = 30) -> Dict:
    """返回全球传染风险矩阵所需的联动指标时间序列.

    - 中美利差倒挂 = 美国10年期国债收益率 - 中国10年期国债收益率
    - 铜/油比 = 伦铜价格 / 原油价格
    - 新兴市场货币指数 = EEM ETF 回撤压力（0-100，越高越危险），以 100 为基准反向展示
    """
    since = datetime.utcnow() - timedelta(days=days)

    async def series_by_code(code: str):
        result = await session.execute(select(Indicator).where(Indicator.code == code))
        ind = result.scalar_one_or_none()
        if not ind:
            return []
        rows = await session.execute(
            select(IndicatorSnapshot)
            .where(
                IndicatorSnapshot.indicator_id == ind.id,
                IndicatorSnapshot.timestamp >= since,
            )
            .order_by(IndicatorSnapshot.timestamp)
        )
        return [(r.timestamp, r.value) for r in rows.scalars().all()]

    us_yield = await series_by_code("us_10y_yield")
    cn_yield = await series_by_code("china_10y_yield")
    copper = await series_by_code("copper_price")
    oil = await series_by_code("oil_price")
    em = await series_by_code("em_fx_stress")

    # 以日期为 key 对齐数据
    dates_set = set()
    for series in (us_yield, cn_yield, copper, oil, em):
        for ts, _ in series:
            dates_set.add(ts.date())
    dates = sorted(dates_set)

    def to_daily_map(series):
        return {ts.date(): value for ts, value in series}

    us_map = to_daily_map(us_yield)
    cn_map = to_daily_map(cn_yield)
    copper_map = to_daily_map(copper)
    oil_map = to_daily_map(oil)
    em_map = to_daily_map(em)

    spread_series = []
    ratio_series = []
    em_series = []
    for d in dates:
        spread = None
        if d in us_map and d in cn_map:
            spread = round(us_map[d] - cn_map[d], 2)

        ratio = None
        if d in copper_map and d in oil_map and oil_map[d]:
            ratio = round(copper_map[d] / oil_map[d], 3)

        em_value = None
        if d in em_map:
            # EEM 风险分越高越危险，这里反向为“指数”形式（100 = 安全）
            em_value = round(max(0, 100 - em_map[d]), 2)

        spread_series.append(spread)
        ratio_series.append(ratio)
        em_series.append(em_value)

    date_labels = [d.strftime("%m-%d") for d in dates]
    return {
        "dates": date_labels,
        "series": [
            {"name": "中美利差倒挂", "data": spread_series, "unit": "%"},
            {"name": "铜/油比", "data": ratio_series, "unit": "x"},
            {"name": "新兴市场货币指数", "data": em_series, "unit": "点"},
        ],
    }
