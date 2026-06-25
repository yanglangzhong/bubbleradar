"""数据校验与异常处理工具."""
import math
from typing import Dict, List, Optional, Tuple


# 指标合理范围（绝对物理/市场边界），超出则视为脏数据
_HARD_BOUNDS: Dict[str, Tuple[Optional[float], Optional[float]]] = {
    "ai_pe_premium": (0.5, 10.0),
    "ai_funding": (0.0, 100.0),
    "ai_compute": (0.0, 100.0),
    "ai_sentiment": (0.0, 100.0),
    "ai_vix": (0.0, 100.0),
    "housing": (0.0, 100.0),
    "debt": (0.0, 100.0),
    "bank": (0.0, 100.0),
    "fx": (0.0, 100.0),
    "real_economy": (0.0, 100.0),
    "capital_market": (0.0, 100.0),
    "china_equity": (0.0, 100.0),
    "china_tech": (0.0, 100.0),
    "china_internet": (0.0, 100.0),
    "china_credit": (0.0, 100.0),
    "china_fx": (0.0, 100.0),
    "second_hand_listing": (0.0, 100.0),
    "land_auction_premium": (0.0, 100.0),
    "us_yield_curve": (0.0, 100.0),
    "credit_spread": (0.0, 20.0),
    "dxy_strength": (50.0, 150.0),
    "em_fx_stress": (0.0, 100.0),
    "commodity_stress": (0.0, 100.0),
    "global_risk_proxy": (0.0, 100.0),
    "global_europe": (0.0, 100.0),
    "global_japan": (0.0, 100.0),
    "global_india": (0.0, 100.0),
    "crypto_btc": (0.0, 100.0),
    "crypto_eth": (0.0, 100.0),
    "crypto_ai_coins": (0.0, 100.0),
    "crypto_miners": (0.0, 100.0),
    "copper_price": (0.5, 20.0),
    "oil_price": (5.0, 200.0),
    "us_10y_yield": (-2.0, 15.0),
    "us_2y_yield": (-2.0, 15.0),
    "china_10y_yield": (0.0, 10.0),
    "sp500": (0.0, None),
    "nasdaq": (0.0, None),
}

# 指标最大日波动（超过则视为可疑），用于抑制异常跳变
_MAX_DAILY_JUMP: Dict[str, float] = {
    "ai_pe_premium": 0.5,
    "ai_funding": 25.0,
    "ai_compute": 15.0,
    "ai_sentiment": 20.0,
    "ai_vix": 15.0,
    "housing": 10.0,
    "debt": 10.0,
    "bank": 10.0,
    "fx": 10.0,
    "real_economy": 5.0,
    "capital_market": 15.0,
    "china_equity": 15.0,
    "china_tech": 15.0,
    "china_internet": 15.0,
    "china_credit": 10.0,
    "china_fx": 10.0,
    "second_hand_listing": 10.0,
    "land_auction_premium": 10.0,
    "us_yield_curve": 20.0,
    "credit_spread": 1.0,
    "dxy_strength": 3.0,
    "em_fx_stress": 10.0,
    "commodity_stress": 10.0,
    "global_risk_proxy": 15.0,
    "global_europe": 10.0,
    "global_japan": 10.0,
    "global_india": 10.0,
    "crypto_btc": 20.0,
    "crypto_eth": 20.0,
    "crypto_ai_coins": 25.0,
    "crypto_miners": 20.0,
    "copper_price": 0.5,
    "oil_price": 15.0,
    "us_10y_yield": 0.5,
    "china_10y_yield": 0.3,
}


def validate_value(code: str, value: float) -> Tuple[bool, Optional[str]]:
    """校验单个指标值是否在合理范围内且为有限数值."""
    if not isinstance(value, (int, float)):
        return False, f"{code}: 非数值 {value!r}"
    if math.isnan(value) or math.isinf(value):
        return False, f"{code}: NaN/Inf"

    low, high = _HARD_BOUNDS.get(code, (None, None))
    if low is not None and value < low:
        return False, f"{code}: {value} 低于硬边界 {low}"
    if high is not None and value > high:
        return False, f"{code}: {value} 高于硬边界 {high}"
    return True, None


def filter_valid_values(values: Dict[str, float], code: str) -> Dict[str, float]:
    """过滤掉校验失败的指标值，并记录原因."""
    valid: Dict[str, float] = {}
    errors: List[str] = []
    for k, v in values.items():
        ok, msg = validate_value(k, v)
        if ok:
            valid[k] = v
        else:
            errors.append(msg or f"{k}: 校验失败")
    if errors:
        # 将错误信息附加到返回字典的元数据中，runner 会处理
        valid["_validation_errors"] = errors  # type: ignore[assignment]
    return valid


def detect_jump(code: str, current: float, previous: Optional[float]) -> Optional[str]:
    """检测相对上一期快照是否存在异常跳变."""
    if previous is None:
        return None
    max_jump = _MAX_DAILY_JUMP.get(code)
    if max_jump is None:
        return None
    if abs(current - previous) > max_jump:
        return f"{code}: 跳变 {current:.2f} vs 上期 {previous:.2f}，超过阈值 {max_jump}"
    return None
