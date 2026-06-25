from datetime import datetime, timedelta
from typing import Dict, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import AlertRule, AlertEvent, Indicator, IndicatorSnapshot
from app.services.calculator import get_latest_snapshot
from app.services.notifier import send_alert_notifications

# 内存冷却表：同一规则最短通知间隔（分钟）
_notify_cooldown_minutes = 30
_last_notified: Dict[int, datetime] = {}


async def check_alert_rules(session: AsyncSession) -> List[AlertEvent]:
    result = await session.execute(select(AlertRule).where(AlertRule.is_active == True))
    rules = result.scalars().all()
    events = []

    for rule in rules:
        triggered = False
        value = None
        message = ""

        if rule.indicator_id:
            snap = await get_latest_snapshot(session, rule.indicator_id)
            if snap:
                value = snap.value
                triggered = _evaluate_condition(value, rule.condition, rule.threshold, rule.threshold_secondary)
                ind = await session.get(Indicator, rule.indicator_id)
                ind_name = ind.name_cn if ind else "未知指标"
                message = f"指标 {ind_name} 当前值 {value} 触发 {rule.condition} {rule.threshold}"

        if triggered and value is not None:
            event = AlertEvent(
                rule_id=rule.id,
                indicator_id=rule.indicator_id,
                value=value,
                threshold=rule.threshold,
                severity=rule.severity,
                message=message,
            )
            session.add(event)
            events.append(event)

            await _maybe_notify(rule, message)

    await session.commit()
    return events


async def _maybe_notify(rule: AlertRule, message: str):
    """按冷却时间控制通知频率，避免同一规则连续轰炸。"""
    now = datetime.utcnow()
    last = _last_notified.get(rule.id)
    if last and (now - last) < timedelta(minutes=_notify_cooldown_minutes):
        return

    await send_alert_notifications(rule.name, message, rule.severity)
    _last_notified[rule.id] = now


def _evaluate_condition(value: float, condition: str, threshold: float, threshold_secondary: float = None) -> bool:
    if condition == "gt":
        return value > threshold
    elif condition == "lt":
        return value < threshold
    elif condition == "eq":
        return abs(value - threshold) < 1e-6
    elif condition == "between":
        return threshold <= value <= (threshold_secondary or threshold)
    return False


async def get_active_alerts(session: AsyncSession, limit: int = 20) -> List[AlertEvent]:
    result = await session.execute(
        select(AlertEvent)
        .where(AlertEvent.acknowledged == False)
        .order_by(desc(AlertEvent.triggered_at))
        .limit(limit)
    )
    return list(result.scalars().all())
