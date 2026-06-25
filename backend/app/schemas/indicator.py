from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class IndicatorBase(BaseModel):
    code: str
    name_cn: str
    name_en: Optional[str] = None
    category: str
    sub_category: Optional[str] = None
    unit: Optional[str] = None
    source: Optional[str] = None
    update_frequency: str = "daily"
    description: Optional[str] = None
    thresholds: dict = {}
    is_simulated: bool = False


class IndicatorCreate(IndicatorBase):
    pass


class IndicatorOut(IndicatorBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_simulated: bool
    created_at: datetime


class IndicatorSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    indicator_id: int
    value: float
    status: str
    timestamp: datetime
    meta: dict


class IndicatorWithValueOut(IndicatorOut):
    latest_value: Optional[float] = None
    latest_status: Optional[str] = None
    latest_timestamp: Optional[datetime] = None
    source_url: Optional[str] = None
