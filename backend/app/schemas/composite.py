from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict


class CompositeScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ai_bubble_score: float
    china_risk_score: float
    global_risk_score: float
    crypto_risk_score: float
    composite_score: float
    timestamp: datetime
    source: str = "历史记录"


class CompositeHistoryOut(BaseModel):
    history: List[CompositeScoreOut]


class ScoreBreakdown(BaseModel):
    category: str
    score: float
    weight: float
    status: str
