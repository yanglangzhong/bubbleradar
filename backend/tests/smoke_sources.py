"""单独测试各数据源抓取器."""
import asyncio
import os
import tempfile

# Windows 下 aiosqlite + :memory: 配合 SQLAlchemy 默认 pool 会挂起，使用临时文件
_test_db_path = tempfile.mktemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{_test_db_path}"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import async_engine
from app.models import Base
from app.crawler.fetchers import FredFetcher, AlphaVantageFetcher


async def main():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(async_engine) as session:
        for cls in [FredFetcher, AlphaVantageFetcher]:
            fetcher = cls()
            print(f"\n--- Testing {fetcher.name} ---")
            try:
                data = await asyncio.wait_for(fetcher.fetch(session), timeout=30)
                print(f"{fetcher.name} OK: {data}")
            except Exception as exc:
                print(f"{fetcher.name} FAILED: {exc}")

    await async_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
