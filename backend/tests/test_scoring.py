"""评分模块单元测试：归一化、状态判定、分类加权、综合评分."""
import os

# 必须在导入 app 之前设置 SQLite，否则默认会尝试连接 PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///:memory:")

import asyncio
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Indicator, IndicatorSnapshot
from app.services.scoring import (
    COMPOSITE_WEIGHTS,
    CATEGORY_WEIGHTS,
    normalize_value,
    get_status,
    calculate_category_score,
    calculate_composite_score,
)


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _make_session():
    engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        return s, engine


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# 1. normalize_value — 安全区
# ---------------------------------------------------------------------------

def test_normalize_value_safe_zone():
    """值低于 watch 阈值，结果应在 0-33 范围内."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    score = normalize_value(20, thresholds)
    assert 0 <= score <= 33
    # 精确验证: (20 / 40) * 33 = 16.5
    assert score == pytest.approx(16.5)


# ---------------------------------------------------------------------------
# 2. normalize_value — 关注区
# ---------------------------------------------------------------------------

def test_normalize_value_watch_zone():
    """值在 watch 和 warning 之间，结果应在 33-66 范围内."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    score = normalize_value(50, thresholds)
    assert 33 <= score <= 66
    # 精确验证: 33 + (50-40)/(60-40) * 33 = 33 + 16.5 = 49.5
    assert score == pytest.approx(49.5)


# ---------------------------------------------------------------------------
# 3. normalize_value — 预警区
# ---------------------------------------------------------------------------

def test_normalize_value_warn_zone():
    """值在 warning 和 danger 之间，结果应在 66-100 范围内."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    score = normalize_value(70, thresholds)
    assert 66 <= score <= 100
    # 精确验证: 66 + (70-60)/(80-60) * 34 = 66 + 17 = 83
    assert score == pytest.approx(83.0)


# ---------------------------------------------------------------------------
# 4. normalize_value — 危险区
# ---------------------------------------------------------------------------

def test_normalize_value_danger_zone():
    """值超过 danger 阈值，结果应截断到 100."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    score = normalize_value(200, thresholds)
    assert score == 100.0

    # 略微超过 danger，但 extra 不够大，应 < 100
    score2 = normalize_value(85, thresholds)
    # extra = (85-80)/80 * 20 = 1.25, total = 101.25 -> min(100, 101.25) = 100
    assert score2 == 100.0


# ---------------------------------------------------------------------------
# 5. normalize_value — watch=0 边界
# ---------------------------------------------------------------------------

def test_normalize_value_zero_watch():
    """watch 阈值为 0 时，安全区结果应为 0."""
    thresholds = {"watch": 0, "warning": 60, "danger": 80}
    score = normalize_value(0, thresholds)
    assert score == 0.0

    # 负值也应在安全区，但 watch=0 时直接返回 0
    score_neg = normalize_value(-5, thresholds)
    assert score_neg == 0.0


# ---------------------------------------------------------------------------
# 6. normalize_value — watch == warning 边界
# ---------------------------------------------------------------------------

def test_normalize_value_equal_thresholds():
    """watch == warning 时，关注区应返回 33.0."""
    thresholds = {"watch": 50, "warning": 50, "danger": 80}
    score = normalize_value(50, thresholds)
    assert score == 33.0

    # warning == danger 时，预警区应返回 66.0
    thresholds2 = {"watch": 40, "warning": 60, "danger": 60}
    score2 = normalize_value(60, thresholds2)
    assert score2 == 66.0


# ---------------------------------------------------------------------------
# 7. normalize_value — 无阈值
# ---------------------------------------------------------------------------

def test_normalize_value_no_thresholds():
    """未配置阈值时，直接返回原值并截断到 0-100."""
    score = normalize_value(50, {})
    assert score == 50.0

    score_high = normalize_value(150, {})
    assert score_high == 100.0

    score_low = normalize_value(-10, {})
    assert score_low == 0.0

    # 部分缺失阈值也应走截断逻辑
    score_partial = normalize_value(30, {"watch": 40})
    assert score_partial == 30.0


# ---------------------------------------------------------------------------
# 8. normalize_value — 负值
# ---------------------------------------------------------------------------

def test_normalize_value_negative():
    """负值在安全区内应产生负分，但 watch > 0 时 (负值/watch)*33 可能为负."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    score = normalize_value(-10, thresholds)
    # (-10 / 40) * 33 = -8.25
    assert score == pytest.approx(-8.25)


# ---------------------------------------------------------------------------
# 9. get_status — safe
# ---------------------------------------------------------------------------

def test_get_status_safe():
    """值低于 watch -> 'safe'."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    assert get_status(20, thresholds) == "safe"
    assert get_status(39.9, thresholds) == "safe"


# ---------------------------------------------------------------------------
# 10. get_status — watch
# ---------------------------------------------------------------------------

def test_get_status_watch():
    """值在 watch 和 warning 之间 -> 'watch'."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    assert get_status(40, thresholds) == "watch"
    assert get_status(50, thresholds) == "watch"
    assert get_status(59.9, thresholds) == "watch"


# ---------------------------------------------------------------------------
# 11. get_status — warn
# ---------------------------------------------------------------------------

def test_get_status_warn():
    """值在 warning 和 danger 之间 -> 'warn'."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    assert get_status(60, thresholds) == "warn"
    assert get_status(70, thresholds) == "warn"
    assert get_status(79.9, thresholds) == "warn"


# ---------------------------------------------------------------------------
# 12. get_status — danger
# ---------------------------------------------------------------------------

def test_get_status_danger():
    """值达到或超过 danger -> 'danger'."""
    thresholds = {"watch": 40, "warning": 60, "danger": 80}
    assert get_status(80, thresholds) == "danger"
    assert get_status(100, thresholds) == "danger"
    assert get_status(200, thresholds) == "danger"


# ---------------------------------------------------------------------------
# 13. get_status — 默认阈值
# ---------------------------------------------------------------------------

def test_get_status_default_thresholds():
    """无阈值时使用默认值 (watch=40, warning=60, danger=80)."""
    assert get_status(30, {}) == "safe"
    assert get_status(50, {}) == "watch"
    assert get_status(70, {}) == "warn"
    assert get_status(90, {}) == "danger"


# ---------------------------------------------------------------------------
# 14. calculate_category_score — 有指标和快照
# ---------------------------------------------------------------------------

def test_calculate_category_score_with_indicators():
    """验证带快照的指标加权计算正确性."""
    async def _run():
        session, engine = await _make_session()
        try:
            # 创建 ai 分类下的两个指标
            ind1 = Indicator(
                code="ai_sentiment",
                name_cn="AI情绪",
                category="ai",
                thresholds={"watch": 40, "warning": 60, "danger": 80},
            )
            ind2 = Indicator(
                code="ai_vix",
                name_cn="AI波动率",
                category="ai",
                thresholds={"watch": 20, "warning": 35, "danger": 50},
            )
            session.add_all([ind1, ind2])
            await session.flush()

            # 创建快照
            snap1 = IndicatorSnapshot(
                indicator_id=ind1.id,
                value=50.0,  # watch zone: 33 + (50-40)/(60-40)*33 = 49.5
                timestamp=datetime.utcnow(),
            )
            snap2 = IndicatorSnapshot(
                indicator_id=ind2.id,
                value=30.0,  # warn zone: 66 + (30-20)/(50-35)*34 = 66 + 22.67 = 88.67
                timestamp=datetime.utcnow(),
            )
            session.add_all([snap1, snap2])
            await session.flush()

            score = await calculate_category_score(session, "ai")

            # 权重: ai_sentiment=0.20, ai_vix=0.10
            # 加权分 = 49.5*0.20 + 88.67*0.10 = 9.9 + 8.867 = 18.767
            # 总权重 = 0.20 + 0.10 = 0.30
            # 加权平均 = 18.767 / 0.30 = 62.56
            expected = round(
                (
                    normalize_value(50.0, ind1.thresholds) * 0.20
                    + normalize_value(30.0, ind2.thresholds) * 0.10
                )
                / (0.20 + 0.10),
                2,
            )
            assert score == expected
        finally:
            await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 15. calculate_category_score — 无指标
# ---------------------------------------------------------------------------

def test_calculate_category_score_empty():
    """分类下无指标时返回 0."""
    async def _run():
        session, engine = await _make_session()
        try:
            score = await calculate_category_score(session, "ai")
            assert score == 0.0
        finally:
            await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 16. calculate_category_score — 指标存在但无快照
# ---------------------------------------------------------------------------

def test_calculate_category_score_missing_snapshot():
    """指标存在但没有快照时应被跳过."""
    async def _run():
        session, engine = await _make_session()
        try:
            ind = Indicator(
                code="ai_sentiment",
                name_cn="AI情绪",
                category="ai",
                thresholds={"watch": 40, "warning": 60, "danger": 80},
            )
            session.add(ind)
            await session.flush()

            score = await calculate_category_score(session, "ai")
            assert score == 0.0
        finally:
            await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 17. calculate_composite_score — 四个分类加权
# ---------------------------------------------------------------------------

def test_calculate_composite_score():
    """验证综合评分正确应用四个分类权重."""
    async def _run():
        session, engine = await _make_session()
        try:
            # 为每个分类创建一个指标和快照
            indicators_data = [
                # ai 分类: value=60 -> watch zone -> 49.5
                ("ai", "ai_sentiment", "AI情绪", {"watch": 40, "warning": 60, "danger": 80}, 60.0),
                # china 分类: value=70 -> warn zone -> 83.0
                ("china", "housing", "房地产", {"watch": 40, "warning": 60, "danger": 80}, 70.0),
                # global 分类: value=20 -> safe zone -> 16.5
                ("global", "us_yield_curve", "美债收益率曲线", {"watch": 40, "warning": 60, "danger": 80}, 20.0),
                # crypto 分类: value=50 -> watch zone -> 49.5
                ("crypto", "crypto_btc", "BTC", {"watch": 40, "warning": 60, "danger": 80}, 50.0),
            ]

            for cat, code, name, thresholds, val in indicators_data:
                ind = Indicator(
                    code=code,
                    name_cn=name,
                    category=cat,
                    thresholds=thresholds,
                )
                session.add(ind)
                await session.flush()

                snap = IndicatorSnapshot(
                    indicator_id=ind.id,
                    value=val,
                    timestamp=datetime.utcnow(),
                )
                session.add(snap)
                await session.flush()

            composite = await calculate_composite_score(session)

            # 每个分类只有一个指标，权重就是该指标在 CATEGORY_WEIGHTS 中的权重
            # ai: score=49.5, weight=0.20 (ai_sentiment)
            # china: score=83.0, weight=0.10 (housing)
            # global: score=16.5, weight=0.15 (us_yield_curve)
            # crypto: score=49.5, weight=0.30 (crypto_btc)

            ai_score = normalize_value(60.0, {"watch": 40, "warning": 60, "danger": 80})
            china_score = normalize_value(70.0, {"watch": 40, "warning": 60, "danger": 80})
            global_score = normalize_value(20.0, {"watch": 40, "warning": 60, "danger": 80})
            crypto_score = normalize_value(50.0, {"watch": 40, "warning": 60, "danger": 80})

            expected = round(
                ai_score * COMPOSITE_WEIGHTS["ai"]
                + china_score * COMPOSITE_WEIGHTS["china"]
                + global_score * COMPOSITE_WEIGHTS["global"]
                + crypto_score * COMPOSITE_WEIGHTS["crypto"],
                2,
            )
            assert composite == expected
        finally:
            await engine.dispose()

    asyncio.run(_run())
