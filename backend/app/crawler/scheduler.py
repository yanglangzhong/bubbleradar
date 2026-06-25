"""定时调度器：使用 APScheduler 定时触发数据采集与告警检查."""
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.logging import get_logger
from app.db.session import AsyncSessionLocal
from app.crawler.runner import run_crawl
from app.services.alert_engine import check_alert_rules

logger = get_logger(__name__)

_scheduler: Optional[AsyncIOScheduler] = None


async def _scheduled_crawl_job():
    async with AsyncSessionLocal() as session:
        try:
            summary = await run_crawl(session)
            logger.info("定时采集完成", summary=summary)
        except Exception as exc:
            logger.exception("定时采集任务失败", error=str(exc))


async def _scheduled_alert_job():
    async with AsyncSessionLocal() as session:
        try:
            events = await check_alert_rules(session)
            if events:
                logger.info("告警检查完成", triggered=len(events))
        except Exception as exc:
            logger.exception("告警检查任务失败", error=str(exc))


def start_scheduler():
    """启动后台定时任务（每 30 分钟采集一次，每 5 分钟检查一次告警规则）."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _scheduled_crawl_job,
        IntervalTrigger(minutes=30),
        id="bubble_radar_crawl",
        replace_existing=True,
    )
    _scheduler.add_job(
        _scheduled_alert_job,
        IntervalTrigger(minutes=5),
        id="bubble_radar_alert",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info("数据采集与告警调度器已启动")


def stop_scheduler():
    """关闭调度器."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown()
        logger.info("数据采集与告警调度器已关闭")
