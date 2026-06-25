"""AI 智能解读：基于风险分数与新闻生成可读分析."""
import logging
from typing import Dict, List, Optional

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _rule_based_insight(
    scores: Dict[str, float],
    news: List[Dict],
    composite: Optional[float] = None,
) -> str:
    """未配置 LLM 时，使用规则模板生成解读."""
    ai = scores.get("ai_bubble", 0)
    china = scores.get("china_risk", 0)
    global_ = scores.get("global_risk", 0)
    crypto = scores.get("crypto_risk", 0)
    comp = composite or round(ai * 0.30 + china * 0.30 + global_ * 0.25 + crypto * 0.15, 2)

    parts = []
    if comp >= 70:
        parts.append("当前综合风险处于高位，建议降低风险敞口、增加防御性资产配置。")
    elif comp >= 50:
        parts.append("当前综合风险中等偏高，建议保持谨慎，关注关键指标变化。")
    else:
        parts.append("当前综合风险相对可控，可维持现有仓位但需持续监控。")

    max_category = max(
        [("AI 泡沫", ai), ("中国风险", china), ("全球风险", global_), ("加密风险", crypto)],
        key=lambda x: x[1],
    )
    parts.append(f"其中【{max_category[0]}】最为突出（{max_category[1]:.1f} 分），是近期主要矛盾。")

    if ai >= 70:
        parts.append("AI 板块估值与情绪均处高位，注意算力链回撤与融资热度回落。")
    if china >= 70:
        parts.append("中国风险指标亮起红灯，房地产、地方债务与资本市场压力需要重点关注。")
    if global_ >= 70:
        parts.append("全球流动性与信用环境趋紧，美元强势和新兴市场货币压力值得警惕。")
    if crypto >= 70:
        parts.append("加密资产投机情绪过热，BTC/ETH 回撤与 AI 概念币热度需警惕。")

    # 从新闻中提取高影响力负面标题
    negative_news = [
        n for n in news
        if n.get("sentiment_score", 0) < -0.2 and n.get("impact_score", 0) >= 50
    ][:2]
    if negative_news:
        titles = "、".join([n.get("title", "") for n in negative_news])
        parts.append(f"近期负面舆情：{titles}。")

    return " ".join(parts)


async def generate_insight(
    scores: Dict[str, float],
    news: List[Dict],
    composite: Optional[float] = None,
) -> Dict[str, str]:
    """生成 AI 智能解读，优先使用 LLM，失败则回退到规则模板."""
    settings = get_settings()
    api_key = getattr(settings, "OPENAI_API_KEY", None) or ""

    rule_insight = _rule_based_insight(scores, news, composite)

    if not api_key or api_key in ("your-openai-api-key", ""):
        return {
            "insight": rule_insight,
            "summary": _news_summary(news),
            "model": "rule-based",
            "notice": "未配置 OPENAI_API_KEY，当前使用规则模板解读。",
        }

    prompt = _build_prompt(scores, news, composite)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "你是一位宏观风险分析师，擅长用简洁的中文解读市场风险。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.7,
                    "max_tokens": 600,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()
            return {
                "insight": content,
                "summary": _news_summary(news),
                "model": "gpt-4o-mini",
                "notice": "",
            }
    except Exception as exc:
        logger.warning("LLM 解读失败，回退到规则模板: %s", exc)
        return {
            "insight": rule_insight,
            "summary": _news_summary(news),
            "model": "rule-based",
            "notice": f"LLM 调用失败（{exc}），已回退到规则模板。",
        }


def _news_summary(news: List[Dict]) -> str:
    """基于新闻情绪生成一句话市场共识摘要."""
    if not news:
        return "近期暂无重大新闻。"
    negative = [n for n in news if n.get("sentiment_score", 0) < -0.1]
    positive = [n for n in news if n.get("sentiment_score", 0) > 0.1]
    high_impact = [n for n in news if n.get("impact_score", 0) >= 60]

    if len(negative) > len(positive) and high_impact:
        return f"市场情绪偏负面，过去 {len(news)} 条新闻中负面占多数，且出现 {len(high_impact)} 条高影响事件。"
    if len(positive) > len(negative):
        return f"市场情绪相对积极，正面新闻占比更高，但需警惕突发风险。"
    return f"市场情绪分化，{len(news)} 条新闻中多空交织，建议关注高影响事件。"


def _build_prompt(
    scores: Dict[str, float],
    news: List[Dict],
    composite: Optional[float],
) -> str:
    ai = scores.get("ai_bubble", 0)
    china = scores.get("china_risk", 0)
    global_ = scores.get("global_risk", 0)
    crypto = scores.get("crypto_risk", 0)
    comp = composite or round(ai * 0.30 + china * 0.30 + global_ * 0.25 + crypto * 0.15, 2)

    news_text = "\n".join(
        f"- {n.get('title', '')}（来源：{n.get('source', '未知')}，情绪{n.get('sentiment_score', 0):.2f}）"
        for n in news[:8]
    )

    return (
        f"请基于以下风险分数和新闻，生成一段 200 字以内的中文市场解读：\n\n"
        f"综合风险分：{comp:.1f}/100\n"
        f"AI 泡沫：{ai:.1f}/100\n"
        f"中国风险：{china:.1f}/100\n"
        f"全球风险：{global_:.1f}/100\n"
        f"加密风险：{crypto:.1f}/100\n\n"
        f"近期新闻：\n{news_text}\n\n"
        "要求：1）指出当前最大风险点；2）给出一句简洁的投资建议；3）语言专业但易懂。"
    )
