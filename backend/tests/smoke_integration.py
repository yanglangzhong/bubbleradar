"""集成冒烟测试：初始化数据库、种子数据并执行一次完整爬取."""
import os
import asyncio
import tempfile

# Windows 下 aiosqlite + :memory: 配合 SQLAlchemy 默认 pool 会挂起，使用临时文件
_test_db_path = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal, async_engine
from app.models import Base, Indicator, IndicatorSnapshot, NewsArticle
from scripts.seed import seed
from app.crawler.runner import run_crawl
from app.services.calculator import get_latest_composite


async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        await seed(session)

        indicators = (await session.execute(select(func.count(Indicator.id)))).scalar()
        snapshots = (await session.execute(select(func.count(IndicatorSnapshot.id)))).scalar()
        print(f"Seeded indicators={indicators}, snapshots={snapshots}")

        summary = await run_crawl(session)
        print(f"Crawl created={summary['created']}, skipped={summary['skipped']}, composite={summary['composite']}")

        composite = await get_latest_composite(session)
        print(
            f"Latest composite={composite.composite_score} "
            f"(ai={composite.ai_bubble_score}, china={composite.china_risk_score}, global={composite.global_risk_score})"
        )

        news = (await session.execute(select(func.count(NewsArticle.id)))).scalar()
        print(f"News articles={news}")

    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
