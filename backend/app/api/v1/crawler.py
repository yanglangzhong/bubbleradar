"""数据采集相关 API."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crawler.runner import run_crawl

router = APIRouter(prefix="/crawler", tags=["crawler"])


@router.post("/run")
async def trigger_crawl(session: AsyncSession = Depends(get_db)):
    """手动触发一次数据采集与评分重算."""
    summary = await run_crawl(session)
    return {"status": "ok", **summary}
