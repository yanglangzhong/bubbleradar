from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.schemas import AlertRuleOut, AlertRuleCreate, AlertEventOut
from app.services import check_alert_rules, get_active_alerts
from app.models import AlertRule

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("/rules", response_model=List[AlertRuleOut])
async def list_rules(session: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await session.execute(select(AlertRule))
    return list(result.scalars().all())


@router.post("/rules", response_model=AlertRuleOut)
async def create_rule(rule: AlertRuleCreate, session: AsyncSession = Depends(get_db)):
    db_rule = AlertRule(**rule.model_dump())
    session.add(db_rule)
    await session.commit()
    await session.refresh(db_rule)
    return db_rule


@router.get("/events", response_model=List[AlertEventOut])
async def list_events(session: AsyncSession = Depends(get_db)):
    events = await get_active_alerts(session)
    return events


@router.post("/check")
async def check_alerts(session: AsyncSession = Depends(get_db)):
    events = await check_alert_rules(session)
    return {"triggered": len(events)}
