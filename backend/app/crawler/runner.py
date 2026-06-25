"""采集执行器：协调多个抓取器，写入快照并触发计算/预警."""
import logging
from datetime import datetime
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crawler.fetchers import YahooFetcher, FredFetcher, AlphaVantageFetcher, EastmoneyFetcher, AkShareFetcher, FallbackFetcher
from app.models import Indicator, IndicatorSnapshot
from app.services.scoring import get_status
from app.services.calculator import calculate_composite_score
from app.services.alert_engine import check_alert_rules
from app.services.news_crawler import crawl_news

logger = logging.getLogger(__name__)

_FETCHERS = [YahooFetcher(), FredFetcher(), AlphaVantageFetcher(), EastmoneyFetcher(), AkShareFetcher()]
_FALLBACK = FallbackFetcher()


async def run_crawl(session: AsyncSession) -> Dict:
    """执行一次完整的数据采集流程."""
    fetched: Dict[str, float] = {}
    sources: Dict[str, str] = {}
    source_errors: Dict[str, str] = {}

    for fetcher in _FETCHERS:
        try:
            data = await fetcher.fetch(session)
            logger.info("%s 抓取到 %d 条指标", fetcher.name, len(data))
            for k, v in data.items():
                fetched[k] = v
                sources[k] = fetcher.name
        except Exception as exc:
            err_msg = str(exc)
            source_errors[fetcher.name] = err_msg
            logger.warning("%s 执行失败: %s", fetcher.name, err_msg)

    # 兜底补充未抓取的指标
    try:
        fallback_data = await _FALLBACK.fetch_missing(session, fetched)
        for k, v in fallback_data.items():
            fetched[k] = v
            sources[k] = "历史基线（无新数据）"
        logger.info("兜底补充 %d 条指标", len(fallback_data))
    except Exception as exc:
        source_errors["fallback"] = str(exc)
        logger.warning("兜底抓取失败: %s", exc)

    # 写入快照
    result = await session.execute(select(Indicator))
    indicators = {ind.code: ind for ind in result.scalars().all()}

    created = 0
    skipped = 0
    for code, value in fetched.items():
        indicator = indicators.get(code)
        if not indicator:
            skipped += 1
            continue

        status = get_status(value, indicator.thresholds or {})
        snapshot = IndicatorSnapshot(
            indicator_id=indicator.id,
            value=value,
            status=status,
            timestamp=datetime.utcnow(),
            meta={"source": sources.get(code, "unknown")},
        )
        session.add(snapshot)
        created += 1

    await session.commit()

    # 重新计算综合评分与预警
    composite = await calculate_composite_score(session)
    alerts = await check_alert_rules(session)

    # 采集新闻情绪
    try:
        news_summary = await crawl_news(session)
        # 将新闻源失败合并到整体 source_errors，便于前端展示
        for src, err in news_summary.get("source_errors", {}).items():
            source_errors[f"news:{src}"] = err
    except Exception as exc:
        logger.warning("新闻采集失败: %s", exc)
        news_summary = {"created": 0, "skipped": 0, "total": 0}

    logger.info(
        "采集完成: 写入 %d 条快照, 跳过 %d 条, 综合分 %.2f, 预警 %d 条, 新闻 %d 条",
        created,
        skipped,
        composite.composite_score,
        len(alerts),
        news_summary.get("created", 0),
    )

    return {
        "created": created,
        "skipped": skipped,
        "fetched": len(fetched),
        "composite": {
            "ai_bubble_score": composite.ai_bubble_score,
            "china_risk_score": composite.china_risk_score,
            "global_risk_score": composite.global_risk_score,
            "composite_score": composite.composite_score,
            "timestamp": composite.timestamp.isoformat(),
        },
        "alerts": len(alerts),
        "news": news_summary,
        "source_errors": source_errors,
    }
