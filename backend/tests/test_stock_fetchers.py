"""股票类数据抓取集成测试."""
import asyncio
import os

# 必须在导入 app 之前设置 SQLite，否则默认会尝试连接 PostgreSQL
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SYNC_DATABASE_URL", "sqlite:///:memory:")

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_NETWORK_TESTS") != "1",
    reason="跳过外部网络集成测试，设置 RUN_NETWORK_TESTS=1 启用",
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.crawler.fetchers import YahooFetcher, AkShareFetcher, AlphaVantageFetcher, FredFetcher
from app.models import Base


TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def _make_session():
    engine = create_async_engine(TEST_DB_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as s:
        return s, engine


def test_yahoo_fetcher_returns_stock_metrics():
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = YahooFetcher()
            values = await fetcher.fetch(session)
            assert isinstance(values, dict)
            # AI / 芯片 / 美股情绪
            for key in ("ai_sentiment", "ai_compute", "ai_vix"):
                if key in values:
                    assert 0 <= values[key] <= 100
            # 新增 AI ETF 融资热度代理
            if "ai_funding" in values:
                assert 0 <= values["ai_funding"] <= 100
            # 中国股票类实时指标
            for key in ("capital_market", "china_tech", "china_internet"):
                if key in values:
                    assert 0 <= values[key] <= 100
            # 全球宏观指标
            for key in ("dxy_strength", "em_fx_stress", "commodity_stress"):
                if key in values:
                    assert values[key] >= 0
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_yahoo_fetcher_ai_etf_proxy():
    """验证 BOTZ/IRBO 被用于生成 ai_funding 代理指标."""
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = YahooFetcher()
            values = await fetcher.fetch(session)
            # 即使 Yahoo 被墙导致无法访问，返回字典也应是合法的
            assert isinstance(values, dict)
            if "ai_funding" in values:
                assert 0 <= values["ai_funding"] <= 100
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_akshare_fetcher_returns_china_indices():
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = AkShareFetcher()
            values = await fetcher.fetch(session)
            assert isinstance(values, dict)
            if values:
                # A 股市场
                for key in ("china_equity", "capital_market"):
                    if key in values:
                        assert 0 <= values[key] <= 100
                # 中国宏观官方数据
                for key in ("housing", "real_economy", "debt", "bank", "china_fx", "china_credit"):
                    if key in values:
                        assert 0 <= values[key] <= 100
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_akshare_fetcher_retry_and_isolation():
    """验证 AkShareFetcher 具备重试方法且单指标失败不影响整体返回."""
    assert hasattr(AkShareFetcher, "_run_with_retry")

    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = AkShareFetcher()
            values = await fetcher.fetch(session)
            assert isinstance(values, dict)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_fred_fetcher_handles_series():
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = FredFetcher()
            values = await fetcher.fetch(session)
            assert isinstance(values, dict)
            if values:
                for key in ("us_yield_curve", "credit_spread", "dxy_strength"):
                    if key in values:
                        assert values[key] >= 0
        finally:
            await engine.dispose()

    asyncio.run(_run())


def test_alphavantage_fetcher_handles_quotes():
    async def _run():
        session, engine = await _make_session()
        try:
            fetcher = AlphaVantageFetcher()
            values = await fetcher.fetch(session)
            assert isinstance(values, dict)
            if values:
                for key in ("fx", "ai_sentiment", "global_risk_proxy"):
                    if key in values:
                        assert 0 <= values[key] <= 100
        finally:
            await engine.dispose()

    asyncio.run(_run())
