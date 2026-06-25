"""独立调度器服务：启动后每 30 分钟执行一次数据采集."""
import asyncio
import logging

from app.db.session import AsyncSessionLocal, async_engine
from app.models import Base
from app.crawler.scheduler import start_scheduler, stop_scheduler
from scripts.seed import seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    # 创建表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 初始化基础数据
    async with AsyncSessionLocal() as session:
        await seed(session)

    start_scheduler()
    logger.info("调度器已启动，每 30 分钟采集一次数据")

    # 保持运行
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
