"""Seed initial indicators and snapshots for demo."""
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import AsyncSessionLocal
from app.models import Indicator, IndicatorSnapshot, CompositeScore, AlertRule, HistoricalEvent


INDICATORS = [
    # AI Bubble
    {"code": "ai_pe_premium", "name_cn": "AI板块PE溢价率", "category": "ai", "sub_category": "valuation", "unit": "x", "source": "Yahoo Finance", "description": "AI半导体ETF（SOXX）相对50日均价的溢价程度，代理AI估值热度", "thresholds": {"watch": 1.5, "warning": 2.0, "danger": 2.5}, "is_simulated": False},
    {"code": "ai_funding", "name_cn": "AI融资热度", "category": "ai", "sub_category": "funding", "unit": "分", "source": "Yahoo Finance", "description": "AI主题ETF（BOTZ / IRBO）20日涨跌幅映射的AI板块投融资热度，公开市场可验证", "thresholds": {"watch": 60, "warning": 75, "danger": 85}, "is_simulated": False},
    {"code": "ai_compute", "name_cn": "算力闲置压力", "category": "ai", "sub_category": "compute", "unit": "%", "source": "Yahoo Finance（代理）", "description": "NVDA/TSM/ASML/SMH 芯片股综合回撤幅度，代理算力供应链压力", "thresholds": {"watch": 40, "warning": 50, "danger": 60}, "is_simulated": False},
    {"code": "ai_sentiment", "name_cn": "AI情绪指数", "category": "ai", "sub_category": "sentiment", "unit": "分", "source": "Yahoo Finance（代理）", "description": "NASDAQ 20日涨跌幅映射的情绪代理指标", "thresholds": {"watch": 60, "warning": 80, "danger": 90}, "is_simulated": False},
    {"code": "ai_vix", "name_cn": "AI波动率恐慌", "category": "ai", "sub_category": "volatility", "unit": "点", "source": "Yahoo Finance", "description": "VIX 恐慌指数实时值，代理科技股波动风险", "thresholds": {"watch": 20, "warning": 30, "danger": 40}, "is_simulated": False},
    # China Risk
    {"code": "housing", "name_cn": "房地产风险", "category": "china", "sub_category": "housing", "unit": "分", "source": "国家统计局（via AkShare）", "description": "70城新建商品住宅价格指数同比跌幅映射的房地产压力", "thresholds": {"watch": 50, "warning": 70, "danger": 80}, "is_simulated": False},
    {"code": "debt", "name_cn": "地方债务风险", "category": "china", "sub_category": "debt", "unit": "分", "source": "财政部（via AkShare）", "description": "地方政府债券发行量环比增速代理的地方债务扩张压力", "thresholds": {"watch": 50, "warning": 70, "danger": 80}, "is_simulated": False},
    {"code": "bank", "name_cn": "银行系统风险", "category": "china", "sub_category": "bank", "unit": "分", "source": "央行（via AkShare）", "description": "5年期LPR水平代理的银行系统流动性与息差压力", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "fx", "name_cn": "外汇资本风险", "category": "china", "sub_category": "fx", "unit": "分", "source": "Yahoo Finance / AkShare", "description": "USD/CNY 汇率90日变动映射的资本外流压力", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "real_economy", "name_cn": "实体就业风险", "category": "china", "sub_category": "real", "unit": "分", "source": "国家统计局（via AkShare）", "description": "城镇调查失业率映射的实体经济与就业压力", "thresholds": {"watch": 50, "warning": 65, "danger": 80}, "is_simulated": False},
    {"code": "capital_market", "name_cn": "资本市场风险", "category": "china", "sub_category": "market", "unit": "分", "source": "Yahoo Finance / AkShare", "description": "A股主要指数（上证/沪深300/中证1000）相对近一年高点的综合回撤", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "china_equity", "name_cn": "A股指数回撤", "category": "china", "sub_category": "market", "unit": "分", "source": "AkShare", "description": "上证/沪深300/中证1000相对近一年高点的综合回撤压力", "thresholds": {"watch": 30, "warning": 50, "danger": 70}, "is_simulated": False},
    {"code": "china_tech", "name_cn": "港股科技回撤", "category": "china", "sub_category": "market", "unit": "分", "source": "Yahoo Finance", "description": "恒生科技指数相对近一年高点的回撤压力", "thresholds": {"watch": 30, "warning": 50, "danger": 70}, "is_simulated": False},
    {"code": "china_internet", "name_cn": "中概互联网回撤", "category": "china", "sub_category": "market", "unit": "分", "source": "Yahoo Finance / Alpha Vantage", "description": "KWEB/FXI 中概互联网 ETF 综合回撤压力", "thresholds": {"watch": 30, "warning": 50, "danger": 70}, "is_simulated": False},
    {"code": "china_credit", "name_cn": "中债信用压力", "category": "china", "sub_category": "debt", "unit": "分", "source": "AkShare", "description": "中国10年期国债收益率偏离中性基准的压力", "thresholds": {"watch": 40, "warning": 60, "danger": 80}, "is_simulated": False},
    {"code": "china_fx", "name_cn": "人民币汇率压力", "category": "china", "sub_category": "fx", "unit": "分", "source": "AkShare", "description": "美元兑人民币汇率相对中性基准的压力", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "second_hand_listing", "name_cn": "二手房挂牌压力", "category": "china", "sub_category": "housing", "unit": "分", "source": "Yahoo Finance", "description": "CHIR / TAO 房地产ETF平均回撤，代理二手房挂牌/抛压压力", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "land_auction_premium", "name_cn": "土地溢价风险", "category": "china", "sub_category": "housing", "unit": "分", "source": "东方财富", "description": "东方财富土地溢价指数近1年涨跌幅映射的土地市场热度风险", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    # Global Risk
    {"code": "us_yield_curve", "name_cn": "美债收益率曲线", "category": "global", "sub_category": "rates", "unit": "风险分", "source": "FRED", "description": "10Y-2Y利差倒挂程度映射的风险分", "thresholds": {"watch": 0, "warning": 50, "danger": 100}, "is_simulated": False},
    {"code": "credit_spread", "name_cn": "信用利差", "category": "global", "sub_category": "credit", "unit": "%", "source": "FRED", "description": "美企债期权调整利差（BAML）", "thresholds": {"watch": 2.0, "warning": 3.5, "danger": 5.0}, "is_simulated": False},
    {"code": "dxy_strength", "name_cn": "美元强度", "category": "global", "sub_category": "fx", "unit": "点", "source": "Yahoo Finance", "description": "美元指数（DXY）实时值，代理全球流动性压力", "thresholds": {"watch": 100, "warning": 105, "danger": 110}, "is_simulated": False},
    {"code": "em_fx_stress", "name_cn": "新兴市场货币压力", "category": "global", "sub_category": "em", "unit": "分", "source": "Yahoo Finance", "description": "EEM 新兴市场ETF相对近一年高点的回撤，代理新兴市场货币压力", "thresholds": {"watch": 5, "warning": 10, "danger": 15}, "is_simulated": False},
    {"code": "commodity_stress", "name_cn": "大宗商品压力", "category": "global", "sub_category": "commodity", "unit": "分", "source": "Yahoo Finance", "description": "DBC 商品ETF相对近一年高点的回撤，代理商品供需压力", "thresholds": {"watch": 20, "warning": 30, "danger": 40}, "is_simulated": False},
    {"code": "global_risk_proxy", "name_cn": "美股实时风险代理", "category": "global", "sub_category": "equity", "unit": "分", "source": "Alpha Vantage", "description": "SPY 实时涨跌幅映射的全球风险偏好（美股跌→风险分高）", "thresholds": {"watch": 45, "warning": 60, "danger": 75}, "is_simulated": False},
    {"code": "global_europe", "name_cn": "欧洲股指回撤", "category": "global", "sub_category": "equity", "unit": "分", "source": "Yahoo Finance", "description": "Euro Stoxx 50 / DAX / FTSE 100 平均回撤，代理欧洲市场风险", "thresholds": {"watch": 40, "warning": 55, "danger": 70}, "is_simulated": False},
    {"code": "global_japan", "name_cn": "日经225回撤", "category": "global", "sub_category": "equity", "unit": "分", "source": "Yahoo Finance", "description": "日经225指数相对近一年高点的回撤压力", "thresholds": {"watch": 35, "warning": 50, "danger": 65}, "is_simulated": False},
    {"code": "global_india", "name_cn": "印度Nifty回撤", "category": "global", "sub_category": "equity", "unit": "分", "source": "Yahoo Finance", "description": "印度 Nifty 50 指数相对近一年高点的回撤压力", "thresholds": {"watch": 35, "warning": 50, "danger": 65}, "is_simulated": False},
    # Crypto Risk
    {"code": "crypto_btc", "name_cn": "比特币回撤", "category": "crypto", "sub_category": "btc", "unit": "分", "source": "Yahoo Finance", "description": "BTC 相对近一年高点的回撤压力", "thresholds": {"watch": 30, "warning": 50, "danger": 70}, "is_simulated": False},
    {"code": "crypto_eth", "name_cn": "以太坊回撤", "category": "crypto", "sub_category": "eth", "unit": "分", "source": "Yahoo Finance", "description": "ETH 相对近一年高点的回撤压力", "thresholds": {"watch": 30, "warning": 50, "danger": 70}, "is_simulated": False},
    {"code": "crypto_ai_coins", "name_cn": "AI 概念币热度", "category": "crypto", "sub_category": "ai", "unit": "分", "source": "Yahoo Finance", "description": "AI 概念加密资产（NEAR/FET）涨跌幅映射的投机热度", "thresholds": {"watch": 60, "warning": 75, "danger": 85}, "is_simulated": False},
    {"code": "crypto_miners", "name_cn": "矿股/加密股票", "category": "crypto", "sub_category": "equity", "unit": "分", "source": "Yahoo Finance", "description": "MSTR/COIN 等加密概念股综合回撤", "thresholds": {"watch": 35, "warning": 55, "danger": 75}, "is_simulated": False},
    # Macro raw indicators (not risk scores; used for analytics charts)
    {"code": "copper_price", "name_cn": "伦铜价格", "category": "macro", "sub_category": "commodity", "unit": "USD/lb", "source": "Yahoo Finance", "description": "COMEX 铜期货收盘价，用于计算铜/油比", "thresholds": {}, "is_simulated": False},
    {"code": "oil_price", "name_cn": "原油价格", "category": "macro", "sub_category": "commodity", "unit": "USD/bbl", "source": "Yahoo Finance", "description": "WTI 原油期货收盘价，用于计算铜/油比", "thresholds": {}, "is_simulated": False},
    {"code": "us_10y_yield", "name_cn": "美国10年期国债收益率", "category": "macro", "sub_category": "rates", "unit": "%", "source": "FRED", "description": "美国10年期国债收益率，用于计算中美利差", "thresholds": {}, "is_simulated": False},
    {"code": "china_10y_yield", "name_cn": "中国10年期国债收益率", "category": "macro", "sub_category": "rates", "unit": "%", "source": "AkShare", "description": "中国10年期国债收益率，用于计算中美利差", "thresholds": {}, "is_simulated": False},
]


def status_from_value(value: float, thresholds: dict) -> str:
    if value >= thresholds.get("danger", 80):
        return "danger"
    if value >= thresholds.get("warning", 60):
        return "warn"
    if value >= thresholds.get("watch", 40):
        return "watch"
    return "safe"


async def seed(session: AsyncSession):
    # Seed indicators
    code_to_id = {}
    for ind_data in INDICATORS:
        result = await session.execute(select(Indicator).where(Indicator.code == ind_data["code"]))
        existing = result.scalar_one_or_none()
        if existing:
            code_to_id[ind_data["code"]] = existing.id
            continue
        indicator = Indicator(**ind_data)
        session.add(indicator)
        await session.flush()
        code_to_id[ind_data["code"]] = indicator.id

    # Seed snapshots for last 90 days
    base_values = {
        "ai_pe_premium": 2.3,
        "ai_funding": 68,
        "ai_compute": 60,
        "ai_sentiment": 85,
        "ai_vix": 25,
        "housing": 78,
        "debt": 72,
        "bank": 58,
        "fx": 55,
        "real_economy": 65,
        "capital_market": 52,
        "china_equity": 45,
        "china_tech": 48,
        "china_internet": 50,
        "china_credit": 55,
        "china_fx": 55,
        "us_yield_curve": 50,
        "credit_spread": 3.0,
        "dxy_strength": 103,
        "em_fx_stress": 8,
        "commodity_stress": 25,
        "global_risk_proxy": 50,
        "global_europe": 45,
        "global_japan": 40,
        "global_india": 40,
        "second_hand_listing": 55,
        "land_auction_premium": 50,
        "crypto_btc": 40,
        "crypto_eth": 42,
        "crypto_ai_coins": 65,
        "crypto_miners": 45,
        "copper_price": 4.2,
        "oil_price": 78.0,
        "us_10y_yield": 4.3,
        "china_10y_yield": 2.3,
    }

    now = datetime.utcnow()
    for code, base in base_values.items():
        indicator_id = code_to_id[code]
        # Check if already has snapshots
        result = await session.execute(
            select(IndicatorSnapshot).where(IndicatorSnapshot.indicator_id == indicator_id)
        )
        if result.scalars().first():
            continue

        snapshots = []
        for i in range(90, -1, -1):
            ts = now - timedelta(days=i)
            # 为不同量级指标生成合理波动
            band = max(abs(base) * 0.04, 1.5)
            value = base + random.uniform(-band, band) + (90 - i) * random.uniform(-base * 0.0005, base * 0.0008)
            value = max(0, value)
            ind = next(x for x in INDICATORS if x["code"] == code)
            snapshots.append(IndicatorSnapshot(
                indicator_id=indicator_id,
                value=round(value, 2),
                status=status_from_value(value, ind["thresholds"]),
                timestamp=ts,
            ))
        session.add_all(snapshots)

    # Seed alert rules
    result = await session.execute(select(AlertRule))
    if not result.scalars().first():
        rules = [
            AlertRule(name="AI情绪指数过高", indicator_id=code_to_id["ai_sentiment"], condition="gt", threshold=80, severity="warn"),
            AlertRule(name="房地产风险红灯", indicator_id=code_to_id["housing"], condition="gt", threshold=75, severity="danger"),
            AlertRule(name="中美利差倒挂加深", condition="lt", threshold=-2.5, severity="watch"),
        ]
        session.add_all(rules)

    await seed_events(session)

    await session.commit()


async def seed_events(session: AsyncSession):
    """如果历史事件表为空，则插入内置重大事件."""
    result = await session.execute(select(HistoricalEvent))
    if result.scalars().first():
        return

    events = [
        HistoricalEvent(date=datetime(2008, 9, 15).date(), title="雷曼兄弟破产", category="crisis", description="2008 年全球金融危机的标志性事件", source="history"),
        HistoricalEvent(date=datetime(2020, 3, 11).date(), title="WHO宣布新冠大流行", category="pandemic", description="世界卫生组织宣布 COVID-19 为全球大流行", source="history"),
        HistoricalEvent(date=datetime(2022, 2, 24).date(), title="俄乌冲突爆发", category="geopolitics", description="俄罗斯对乌克兰发起特别军事行动", source="history"),
        HistoricalEvent(date=datetime(2022, 3, 16).date(), title="美联储加息周期启动", category="monetary", description="美联储进入新一轮加息周期", source="history"),
        HistoricalEvent(date=datetime(2023, 3, 10).date(), title="硅谷银行破产", category="crisis", description="硅谷银行（SVB）倒闭，引发美国银行业震荡", source="history"),
        HistoricalEvent(date=datetime(2024, 1, 1).date(), title="红海航运危机", category="geopolitics", description="红海航线受袭导致全球航运受阻", source="history"),
        HistoricalEvent(date=datetime(2025, 4, 2).date(), title="美国对华关税升级", category="trade", description="美国对中国商品加征新一轮关税", source="history"),
    ]
    session.add_all(events)


async def main():
    from app.db.session import async_engine
    from app.models import Base
    # 先创建表（避免新数据库无表结构时报错）
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed(session)
    print("Seeded successfully")


if __name__ == "__main__":
    asyncio.run(main())
