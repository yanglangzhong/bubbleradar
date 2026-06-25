"""采集器基类与 FallbackFetcher 单元测试."""
import os

# 必须在导入 app 之前设置 SQLite，否则默认会尝试连接 PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///:memory:")

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, Indicator, IndicatorSnapshot
from app.crawler.base import BaseFetcher
from app.crawler.fetchers import FallbackFetcher, FALLBACK_BASES


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


# ---------------------------------------------------------------------------
# 1. BaseFetcher 接口契约
# ---------------------------------------------------------------------------

def test_base_fetcher_is_abstract():
    """BaseFetcher 是抽象类，不能直接实例化."""
    with pytest.raises(TypeError):
        BaseFetcher()


def test_base_fetcher_subclass_must_implement_fetch():
    """子类必须实现 fetch 方法，否则实例化失败."""
    class IncompleteFetcher(BaseFetcher):
        name = "incomplete"
        # 故意不实现 fetch

    with pytest.raises(TypeError):
        IncompleteFetcher()


def test_base_fetcher_concrete_subclass():
    """正确实现 fetch 的子类可以正常实例化."""
    class DummyFetcher(BaseFetcher):
        name = "dummy"

        async def fetch(self, session):
            return {"dummy_indicator": 42.0}

    fetcher = DummyFetcher()
    assert fetcher.name == "dummy"
    assert hasattr(fetcher, "fetch")


def test_base_fetcher_fetch_returns_dict():
    """fetch 方法应返回 Dict[str, float]."""
    class DummyFetcher(BaseFetcher):
        name = "dummy"

        async def fetch(self, session):
            return {"key": 1.0}

    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = DummyFetcher()
            result = await fetcher.fetch(session)
            assert isinstance(result, dict)
            assert result["key"] == 1.0
        finally:
            await engine.dispose()

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 2. FallbackFetcher — fetch 返回空字典
# ---------------------------------------------------------------------------

def test_fallback_fetcher_fetch_returns_empty():
    """FallbackFetcher.fetch 应返回空字典."""
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = FallbackFetcher()
            result = await fetcher.fetch(session)
            assert result == {}
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_has_name():
    """FallbackFetcher.name 应为 'fallback'."""
    fetcher = FallbackFetcher()
    assert fetcher.name == "fallback"


# ---------------------------------------------------------------------------
# 3. FallbackFetcher — fetch_missing 从快照补充缺失指标
# ---------------------------------------------------------------------------

def test_fallback_fetcher_missing_from_snapshot():
    """fetch_missing 应从最新快照补充未被采集的指标."""
    async def _run():
        session, engine = await _make_session()
        try:
            # 创建指标和快照
            ind = Indicator(
                code="ai_sentiment",
                name_cn="AI情绪",
                category="ai",
                thresholds={"watch": 40, "warning": 60, "danger": 80},
            )
            session.add(ind)
            await session.flush()

            snap = IndicatorSnapshot(
                indicator_id=ind.id,
                value=75.5,
                timestamp=datetime.utcnow(),
            )
            session.add(snap)
            await session.flush()

            fetcher = FallbackFetcher()
            already_fetched = {}  # 没有任何已采集的数据
            result = await fetcher.fetch_missing(session, already_fetched)

            assert "ai_sentiment" in result
            assert result["ai_sentiment"] == 75.5
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_missing_skips_already_fetched():
    """fetch_missing 应跳过 already_fetched 中已有的指标."""
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

            snap = IndicatorSnapshot(
                indicator_id=ind.id,
                value=75.5,
                timestamp=datetime.utcnow(),
            )
            session.add(snap)
            await session.flush()

            fetcher = FallbackFetcher()
            already_fetched = {"ai_sentiment": 99.9}  # 已采集
            result = await fetcher.fetch_missing(session, already_fetched)

            # ai_sentiment 已在 already_fetched 中，不应出现在结果中
            assert "ai_sentiment" not in result
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_missing_uses_default_when_no_snapshot():
    """无快照时使用 FALLBACK_BASES 中的默认值，最终兜底 50."""
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
            # 不创建快照

            fetcher = FallbackFetcher()
            already_fetched = {}
            result = await fetcher.fetch_missing(session, already_fetched)

            # ai_sentiment 在 FALLBACK_BASES 中有默认值 85
            assert "ai_sentiment" in result
            assert result["ai_sentiment"] == 85.0
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_missing_unknown_code_defaults_to_50():
    """不在 FALLBACK_BASES 中的指标代码，无快照时默认为 50."""
    async def _run():
        session, engine = await _make_session()
        try:
            ind = Indicator(
                code="totally_unknown_indicator_xyz",
                name_cn="未知指标",
                category="ai",
                thresholds={},
            )
            session.add(ind)
            await session.flush()

            fetcher = FallbackFetcher()
            already_fetched = {}
            result = await fetcher.fetch_missing(session, already_fetched)

            assert "totally_unknown_indicator_xyz" in result
            assert result["totally_unknown_indicator_xyz"] == 50.0
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_missing_uses_latest_snapshot():
    """有多个快照时，应使用最新的一条."""
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

            # 旧快照
            old_snap = IndicatorSnapshot(
                indicator_id=ind.id,
                value=30.0,
                timestamp=datetime(2024, 1, 1),
            )
            session.add(old_snap)
            await session.flush()

            # 新快照
            new_snap = IndicatorSnapshot(
                indicator_id=ind.id,
                value=88.8,
                timestamp=datetime(2025, 6, 1),
            )
            session.add(new_snap)
            await session.flush()

            fetcher = FallbackFetcher()
            already_fetched = {}
            result = await fetcher.fetch_missing(session, already_fetched)

            assert result["ai_sentiment"] == 88.8
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fallback_fetcher_missing_mixed_scenario():
    """混合场景：部分已采集、部分有快照、部分无快照."""
    async def _run():
        session, engine = await _make_session()
        try:
            # 指标 A: 已采集
            ind_a = Indicator(
                code="ai_sentiment",
                name_cn="AI情绪",
                category="ai",
                thresholds={},
            )
            # 指标 B: 有快照
            ind_b = Indicator(
                code="ai_vix",
                name_cn="AI波动率",
                category="ai",
                thresholds={},
            )
            # 指标 C: 无快照，不在 FALLBACK_BASES 中
            ind_c = Indicator(
                code="unknown_xyz",
                name_cn="未知",
                category="ai",
                thresholds={},
            )
            session.add_all([ind_a, ind_b, ind_c])
            await session.flush()

            snap_b = IndicatorSnapshot(
                indicator_id=ind_b.id,
                value=42.0,
                timestamp=datetime.utcnow(),
            )
            session.add(snap_b)
            await session.flush()

            fetcher = FallbackFetcher()
            already_fetched = {"ai_sentiment": 99.9}
            result = await fetcher.fetch_missing(session, already_fetched)

            # A 已采集 -> 不在结果中
            assert "ai_sentiment" not in result
            # B 有快照 -> 使用快照值
            assert result["ai_vix"] == 42.0
            # C 无快照且未知 -> 默认 50
            assert result["unknown_xyz"] == 50.0
        finally:
            await engine.dispose()

    asyncio.run(_run())
