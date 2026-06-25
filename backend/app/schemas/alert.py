from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class AlertRuleBase(BaseModel):
    name: str
    indicator_id: Optional[int] = None
    condition: str
    threshold: float
    threshold_secondary: Optional[float] = None
    severity: str = "watch"
    is_active: bool = True


class AlertRuleCreate(AlertRuleBase):
    pass


class AlertRuleOut(AlertRuleBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class AlertEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: int
    indicator_id: Optional[int]
    value: float
    threshold: float
    severity: str
    message: str
    triggered_at: datetime
    acknowledged: bool
