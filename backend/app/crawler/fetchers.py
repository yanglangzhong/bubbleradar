"""具体数据抓取器实现."""
import asyncio
import logging
import random
from typing import Dict, List, Optional

import httpx
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.crawler.base import BaseFetcher
from app.crawler.retry import async_retry
from app.crawler.validation import validate_value
from app.models import Indicator
from app.services.scoring import get_latest_snapshot

logger = logging.getLogger(__name__)

# 指标兜底基线（与 scripts/seed.py 保持一致，便于首次运行）
FALLBACK_BASES: Dict[str, float] = {
    "ai_pe_premium": 2.3,
    "ai_funding": 2748,
    "ai_compute": 60,
    "ai_sentiment": 85,
    "ai_vix": 25,
    "housing": 78,
    "debt": 72,
    "bank": 58,
    "fx": 55,
    "real_economy": 65,
    "capital_market": 52,
    "china_tech": 48,
    "china_internet": 50,
    "global_risk_proxy": 50,
    "us_yield_curve": 50,
    "credit_spread": 3.0,
    "dxy_strength": 103,
    "em_fx_stress": 8,
    "commodity_stress": 25,
    "global_europe": 45,
    "global_japan": 40,
    "global_india": 40,
    "second_hand_listing": 55,
    "land_auction_premium": 50,
    "copper_price": 4.2,
    "oil_price": 78.0,
    "us_10y_yield": 4.3,
    "china_10y_yield": 2.3,
}


def _clamp(value: float, low: float = 0, high: float = 100) -> float:
    return max(low, min(high, value))


def _validate_values(values: Dict[str, float], source: str) -> Dict[str, float]:
    """过滤掉越界/非法的指标值，并记录日志."""
    valid: Dict[str, float] = {}
    for code, value in values.items():
        ok, msg = validate_value(code, value)
        if ok:
            valid[code] = value
        else:
            logger.warning("[%s] 数据校验失败: %s", source, msg)
    return valid


class YahooFetcher(BaseFetcher):
    """通过 Yahoo Finance 获取市场数据并映射为内部指标."""

    name = "yahoo"

    _TICKERS = {
        # AI / 美股核心
        "soxx": "SOXX",
        "ixic": "^IXIC",
        "nvda": "NVDA",
        "spx": "^GSPC",
        "smh": "SMH",
        "tsm": "TSM",
        "asml": "ASML",
        # AI 主题 ETF，代理 AI 融资/投资热度（Crunchbase 无免费权威 API）
        "botz": "BOTZ",
        "irbo": "IRBO",
        # 中国资产
        "sh": "000001.SS",
        "csi300": "000300.SS",
        "csi1000": "000852.SS",
        "hsi": "^HSI",
        "hstech": "^HSTECH",
        "kweb": "KWEB",
        "fxi": "FXI",
        # 全球宏观
        "cny": "CNY=X",
        "vix": "^VIX",
        "dxy": "DX-Y.NYB",
        "eem": "EEM",
        "dbc": "DBC",
        # 全球主要股指
        "euro_stoxx50": "^STOXX50E",
        "dax": "^GDAXI",
        "ftse": "^FTSE",
        "nikkei": "^N225",
        "nifty": "^NSEI",
        # 中国房地产高频代理 ETF
        "chir": "CHIR",
        "tao": "TAO",
        # 大宗商品
        "copper": "HG=F",
        "oil": "CL=F",
        # 加密货币
        "btc": "BTC-USD",
        "eth": "ETH-USD",
        "near": "NEAR-USD",
        "fet": "FET-USD",
        "mstr": "MSTR",
        "coin": "COIN",
    }

    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        try:
            import yfinance as yf
        except ImportError:
            logger.warning("yfinance 未安装，跳过 Yahoo Finance 采集")
            return {}

        # 将 yfinance 缓存目录限制在项目内，避免沙箱/权限问题
        import os as _os
        cache_dir = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), "..", "..", ".cache", "py-yfinance"))
        _os.makedirs(cache_dir, exist_ok=True)
        try:
            yf.set_tz_cache_location(cache_dir)
        except Exception:
            pass

        loop = asyncio.get_running_loop()
        frames: Dict[str, Optional[object]] = {}

        # 网络受限环境下 Yahoo 经常不可用，缩短超时并快速失败
        consecutive_failures = 0
        for key, ticker in self._TICKERS.items():
            try:
                t = yf.Ticker(ticker)
                hist = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, lambda _t=t: _t.history(period="6mo", interval="1d")
                    ),
                    timeout=3,
                )
                if hist is not None and not hist.empty:
                    frames[key] = hist
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
            except asyncio.TimeoutError:
                logger.warning("Yahoo 抓取 %s 超时，跳过", ticker)
                consecutive_failures += 1
            except Exception as exc:
                logger.warning("Yahoo 抓取 %s 失败: %s", ticker, exc)
                consecutive_failures += 1

            # 连续 3 个 ticker 失败则认为 Yahoo 不可用，跳过剩余请求
            if consecutive_failures >= 3:
                logger.warning("Yahoo Finance 连续失败 3 次，跳过剩余 ticker")
                break

        values = self._compute(frames)
        return _validate_values(values, self.name)

    @staticmethod
    def _compute(frames: Dict[str, Optional[object]]) -> Dict[str, float]:
        values: Dict[str, float] = {}

        def close_of(key: str):
            frame = frames.get(key)
            if frame is None or frame.empty:
                return None
            col = "Close" if "Close" in frame.columns else "Adj Close"
            return frame[col].dropna()

        def drawdown_score(series, multiplier=1.0):
            if series is None or series.empty:
                return None
            high = series.max()
            if high == 0:
                return None
            return round(_clamp((1 - series.iloc[-1] / high) * 100 * multiplier), 2)

        soxx = close_of("soxx")
        if soxx is not None and len(soxx) >= 50:
            ma50 = soxx.rolling(50).mean().iloc[-1]
            values["ai_pe_premium"] = round(soxx.iloc[-1] / ma50, 2)

        ixic = close_of("ixic")
        if ixic is not None and len(ixic) >= 20:
            ret20 = (ixic.iloc[-1] - ixic.iloc[-20]) / ixic.iloc[-20]
            values["ai_sentiment"] = round(_clamp(ret20 * 500 + 50), 2)

        # AI 融资热度：用 AI 主题 ETF（BOTZ/IRBO）20 日涨跌幅代理
        botz = close_of("botz")
        irbo = close_of("irbo")
        funding_rets = []
        if botz is not None and len(botz) >= 20:
            funding_rets.append((botz.iloc[-1] - botz.iloc[-20]) / botz.iloc[-20])
        if irbo is not None and len(irbo) >= 20:
            funding_rets.append((irbo.iloc[-1] - irbo.iloc[-20]) / irbo.iloc[-20])
        if funding_rets:
            avg_ret = sum(funding_rets) / len(funding_rets)
            values["ai_funding"] = round(_clamp(avg_ret * 500 + 50), 2)

        # 多维度算力/芯片情绪：NVDA 回撤 + TSM/ASML/SMH 平均回撤
        nvda = close_of("nvda")
        nvda_dd = drawdown_score(nvda)
        tsm = close_of("tsm")
        asml = close_of("asml")
        smh = close_of("smh")
        chip_dds = [d for d in [nvda_dd, drawdown_score(tsm), drawdown_score(asml), drawdown_score(smh)] if d is not None]
        if chip_dds:
            values["ai_compute"] = round(sum(chip_dds) / len(chip_dds), 2)

        vix = close_of("vix")
        if vix is not None and not vix.empty:
            values["ai_vix"] = round(_clamp(vix.iloc[-1], 0, 100), 2)

        # 中国股票类实时指标：上证综指、沪深300、中证1000、港股科技、中概互联
        sh = close_of("sh")
        csi300 = close_of("csi300")
        csi1000 = close_of("csi1000")
        china_equity_dds = [d for d in [
            drawdown_score(sh, 1.2),
            drawdown_score(csi300, 1.2),
            drawdown_score(csi1000, 1.0),
        ] if d is not None]
        if china_equity_dds:
            values["capital_market"] = round(sum(china_equity_dds) / len(china_equity_dds), 2)
            values["china_equity"] = values["capital_market"]

        hstech = close_of("hstech")
        hstech_dd = drawdown_score(hstech, 1.2)
        if hstech_dd is not None:
            values["china_tech"] = hstech_dd

        kweb = close_of("kweb")
        fxi = close_of("fxi")
        internet_dds = [d for d in [drawdown_score(kweb, 1.2), drawdown_score(fxi, 1.0)] if d is not None]
        if internet_dds:
            values["china_internet"] = round(sum(internet_dds) / len(internet_dds), 2)

        cny = close_of("cny")
        if cny is not None and len(cny) >= 90:
            ret90 = (cny.iloc[-1] - cny.iloc[-90]) / cny.iloc[-90]
            values["fx"] = round(_clamp(ret90 * 500 + 55), 2)

        dxy = close_of("dxy")
        if dxy is not None and not dxy.empty:
            values["dxy_strength"] = round(dxy.iloc[-1], 2)

        eem = close_of("eem")
        if eem is not None and not eem.empty:
            high1y = eem.max()
            drawdown = (1 - eem.iloc[-1] / high1y) * 100
            values["em_fx_stress"] = round(_clamp(drawdown * 0.5), 2)

        dbc = close_of("dbc")
        if dbc is not None and not dbc.empty:
            high1y = dbc.max()
            drawdown = (1 - dbc.iloc[-1] / high1y) * 100
            values["commodity_stress"] = round(_clamp(drawdown * 0.5), 2)

        # 加密货币风险指标
        btc = close_of("btc")
        btc_dd = drawdown_score(btc, 1.0)
        if btc_dd is not None:
            values["crypto_btc"] = btc_dd

        eth = close_of("eth")
        eth_dd = drawdown_score(eth, 1.0)
        if eth_dd is not None:
            values["crypto_eth"] = eth_dd

        # AI 概念币热度：NEAR/FET 20日涨跌幅平均
        near = close_of("near")
        fet = close_of("fet")
        ai_coin_rets = []
        if near is not None and len(near) >= 20:
            ai_coin_rets.append((near.iloc[-1] - near.iloc[-20]) / near.iloc[-20])
        if fet is not None and len(fet) >= 20:
            ai_coin_rets.append((fet.iloc[-1] - fet.iloc[-20]) / fet.iloc[-20])
        if ai_coin_rets:
            avg_ret = sum(ai_coin_rets) / len(ai_coin_rets)
            values["crypto_ai_coins"] = round(_clamp(avg_ret * 500 + 50), 2)

        # 加密概念股：MSTR / COIN 综合回撤
        mstr = close_of("mstr")
        coin = close_of("coin")
        crypto_equity_dds = [d for d in [drawdown_score(mstr, 1.0), drawdown_score(coin, 1.0)] if d is not None]
        if crypto_equity_dds:
            values["crypto_miners"] = round(sum(crypto_equity_dds) / len(crypto_equity_dds), 2)

        # 全球主要股指风险代理
        europe_dds = [d for d in [
            drawdown_score(close_of("euro_stoxx50")),
            drawdown_score(close_of("dax")),
            drawdown_score(close_of("ftse")),
        ] if d is not None]
        if europe_dds:
            values["global_europe"] = round(sum(europe_dds) / len(europe_dds), 2)

        nikkei = close_of("nikkei")
        nikkei_dd = drawdown_score(nikkei)
        if nikkei_dd is not None:
            values["global_japan"] = nikkei_dd

        nifty = close_of("nifty")
        nifty_dd = drawdown_score(nifty)
        if nifty_dd is not None:
            values["global_india"] = nifty_dd

        # 中国房地产高频代理：二手房挂牌压力 / 土地溢价
        re_dds = [d for d in [drawdown_score(close_of("chir")), drawdown_score(close_of("tao"))] if d is not None]
        if re_dds:
            values["second_hand_listing"] = round(sum(re_dds) / len(re_dds), 2)

        # 大宗商品原始价格（用于铜/油比等宏观图表）
        copper = close_of("copper")
        if copper is not None and not copper.empty:
            values["copper_price"] = round(float(copper.iloc[-1]), 2)

        oil = close_of("oil")
        if oil is not None and not oil.empty:
            values["oil_price"] = round(float(oil.iloc[-1]), 2)

        return values


class FredFetcher(BaseFetcher):
    """FRED 经济数据采集器（需配置 FRED_API_KEY）."""

    name = "fred"

    _SERIES = {
        "DGS10": "us_10y",
        "DGS2": "us_2y",
        "BAMLC0A0CM": "credit_spread",
        "VIXCLS": "vix",
        "DTWEXBGS": "dxy",
        "SP500": "sp500",
        "NASDAQCOM": "nasdaq",
    }

    @async_retry(retries=2, delay=1.0)
    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        settings = get_settings()
        if not settings.FRED_API_KEY:
            logger.info("FRED_API_KEY 未配置，跳过 FRED 采集")
            return {}

        base_url = "https://api.stlouisfed.org/fred/series/observations"
        values: Dict[str, float] = {}
        us_10y: Optional[float] = None
        us_2y: Optional[float] = None
        equity_series: Dict[str, List[float]] = {}

        async with httpx.AsyncClient(timeout=20) as client:
            for series, key in self._SERIES.items():
                try:
                    # 股指序列需要多期数据计算涨跌幅/均线
                    limit = 30 if key in ("sp500", "nasdaq") else 1
                    resp = await client.get(
                        base_url,
                        params={
                            "series_id": series,
                            "api_key": settings.FRED_API_KEY,
                            "file_type": "json",
                            "sort_order": "desc",
                            "limit": limit,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    obs = [
                        float(o["value"])
                        for o in data.get("observations", [])
                        if o.get("value") not in (None, ".")
                    ]
                    if not obs:
                        continue
                    num = obs[0]
                    if key == "us_10y":
                        us_10y = num
                    elif key == "us_2y":
                        us_2y = num
                    elif key == "credit_spread":
                        values["credit_spread"] = round(num, 2)
                    elif key == "vix":
                        values["ai_vix"] = round(_clamp(num, 0, 100), 2)
                    elif key == "dxy":
                        values["dxy_strength"] = round(num, 2)
                    elif key in ("sp500", "nasdaq"):
                        equity_series[key] = obs
                except Exception as exc:
                    logger.warning("FRED %s 抓取失败: %s", series, exc)

        if us_10y is not None:
            values["us_10y_yield"] = round(us_10y, 2)
        if us_10y is not None and us_2y is not None:
            spread = us_10y - us_2y
            values["us_yield_curve"] = round(_clamp(-spread * 100, 0, 100), 2)

        # 用 FRED 的纳斯达克/标普数据作为 Yahoo 不可用时的 AI 情绪代理
        nasdaq = equity_series.get("nasdaq")
        if nasdaq and len(nasdaq) >= 20:
            ret20 = (nasdaq[0] - nasdaq[19]) / nasdaq[19]
            values["ai_sentiment"] = round(_clamp(ret20 * 500 + 50), 2)
        sp500 = equity_series.get("sp500")
        if sp500 and len(sp500) >= 50:
            ma50 = sum(sp500[:50]) / 50
            values["ai_pe_premium"] = round(sp500[0] / ma50, 2)

        return _validate_values(values, self.name)


class AlphaVantageFetcher(BaseFetcher):
    """Alpha Vantage 补充数据源（外汇、个股实时报价）.

    免费版限制 25 次调用/天，因此只抓取两个核心指标，作为 Yahoo/FRED 的备份。
    """

    name = "alphavantage"

    @staticmethod
    def _check_rate_limit(data: dict) -> bool:
        """检查是否命中 Alpha Vantage 免费版限流提示."""
        note = data.get("Note") or data.get("Information")
        if note and ("call frequency" in note.lower() or "api call frequency" in note.lower()):
            logger.warning("Alpha Vantage 触发限流: %s", note)
            return True
        return False

    @async_retry(retries=1, delay=1.0)
    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        settings = get_settings()
        if not settings.ALPHA_VANTAGE_API_KEY:
            logger.info("ALPHA_VANTAGE_API_KEY 未配置，跳过 Alpha Vantage 采集")
            return {}

        values: Dict[str, float] = {}
        api_key = settings.ALPHA_VANTAGE_API_KEY
        base_url = "https://www.alphavantage.co/query"

        async with httpx.AsyncClient(timeout=10) as client:
            # 1) USD/CNY 日线，用于计算人民币 90 日贬值压力 -> fx
            try:
                resp = await client.get(
                    base_url,
                    params={
                        "function": "FX_DAILY",
                        "from_symbol": "USD",
                        "to_symbol": "CNY",
                        "apikey": api_key,
                        "outputsize": "compact",
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if self._check_rate_limit(data):
                    return values
                ts = data.get("Time Series FX (Daily)", {})
                if ts:
                    dates = sorted(ts.keys())
                    if len(dates) >= 90:
                        close_now = float(ts[dates[-1]]["4. close"])
                        close_90 = float(ts[dates[-90]]["4. close"])
                        ret90 = (close_now - close_90) / close_90
                        values["fx"] = round(_clamp(ret90 * 500 + 55), 2)
                    elif dates:
                        close_now = float(ts[dates[-1]]["4. close"])
                        # 数据不足 90 天，按最新价相对基线 7.1 估算压力
                        values["fx"] = round(_clamp((close_now - 7.1) * 50 + 55), 2)
            except Exception as exc:
                logger.warning("Alpha Vantage FX_DAILY 抓取失败: %s", exc)

            # 2) NVDA 实时报价，涨跌幅映射 AI 情绪 -> ai_sentiment
            try:
                resp = await client.get(
                    base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": "NVDA",
                        "apikey": api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if self._check_rate_limit(data):
                    return values
                quote = data.get("Global Quote", {})
                change_pct = quote.get("10. change percent", "")
                if change_pct:
                    pct = float(change_pct.replace("%", ""))
                    values["ai_sentiment"] = round(_clamp(pct * 10 + 50), 2)
            except Exception as exc:
                logger.warning("Alpha Vantage GLOBAL_QUOTE NVDA 抓取失败: %s", exc)

            # 3) SPY 实时报价，作为全球风险/美股整体情绪的补充
            try:
                resp = await client.get(
                    base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": "SPY",
                        "apikey": api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if self._check_rate_limit(data):
                    return values
                quote = data.get("Global Quote", {})
                change_pct = quote.get("10. change percent", "")
                if change_pct:
                    pct = float(change_pct.replace("%", ""))
                    # 全球风险分与美股整体反向：美股跌 -> 风险分高
                    values["global_risk_proxy"] = round(_clamp(-pct * 10 + 50), 2)
            except Exception as exc:
                logger.warning("Alpha Vantage GLOBAL_QUOTE SPY 抓取失败: %s", exc)

            # 4) KWEB（中概互联网 ETF）实时报价，作为中国互联网情绪补充
            try:
                resp = await client.get(
                    base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": "KWEB",
                        "apikey": api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if self._check_rate_limit(data):
                    return values
                quote = data.get("Global Quote", {})
                change_pct = quote.get("10. change percent", "")
                if change_pct:
                    pct = float(change_pct.replace("%", ""))
                    values["china_internet"] = round(_clamp(-pct * 10 + 50), 2)
            except Exception as exc:
                logger.warning("Alpha Vantage GLOBAL_QUOTE KWEB 抓取失败: %s", exc)

            # 5) TSM（台积电）实时报价，作为 AI 芯片供应链情绪补充
            try:
                resp = await client.get(
                    base_url,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": "TSM",
                        "apikey": api_key,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                if self._check_rate_limit(data):
                    return values
                quote = data.get("Global Quote", {})
                change_pct = quote.get("10. change percent", "")
                if change_pct:
                    pct = float(change_pct.replace("%", ""))
                    # 与 ai_compute 方向一致：跌 -> 压力大
                    chip_stress = round(_clamp(-pct * 10 + 50), 2)
                    if "ai_compute" in values:
                        values["ai_compute"] = round((values["ai_compute"] + chip_stress) / 2, 2)
                    else:
                        values["ai_compute"] = chip_stress
            except Exception as exc:
                logger.warning("Alpha Vantage GLOBAL_QUOTE TSM 抓取失败: %s", exc)

        return _validate_values(values, self.name)


class EastmoneyFetcher(BaseFetcher):
    """东方财富行业指数/土地溢价高频数据抓取."""

    name = "eastmoney"

    @async_retry(retries=2, delay=1.0)
    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        url = "https://data.eastmoney.com/cjsj/hyzs_EMI00120219.html"
        try:
            async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                html = resp.text
        except Exception as exc:
            logger.warning("Eastmoney 页面抓取失败: %s", exc)
            return {}

        try:
            tables = pd.read_html(html)
            if not tables:
                return {}
            df = tables[0]
            # 找到近1年涨跌幅列
            yoy_col = None
            for col in df.columns:
                if "近1年涨跌幅" in str(col):
                    yoy_col = col
                    break
            if yoy_col is None:
                # 尝试包含“涨跌幅”或“近1年”的列
                for col in df.columns:
                    col_str = str(col)
                    if "涨跌幅" in col_str or "近1年" in col_str:
                        yoy_col = col
                        break
            if yoy_col is None:
                return {}
            yoy = float(pd.to_numeric(df.iloc[0][yoy_col], errors="coerce"))
            if pd.isna(yoy):
                return {}
            return _validate_values({"land_auction_premium": round(_clamp(50 - yoy * 1.5), 2)}, self.name)
        except Exception as exc:
            logger.warning("Eastmoney 表格解析失败: %s", exc)
            return {}


class AkShareFetcher(BaseFetcher):
    """中国宏观/市场数据（akshare 可选，未安装则跳过）.

    对每个 akshare 接口做超时 + 重试隔离，单个指标失败不影响其他指标。
    """

    name = "akshare"

    # 单次接口超时（秒），避免某个接口 hang 住整个启动流程
    _TIMEOUT = 12
    # 重试次数（含首次共 retries+1 次）
    _RETRIES = 2

    @staticmethod
    async def _run_with_retry(loop, fn, name: str, retries: int = _RETRIES, timeout: float = _TIMEOUT):
        """对同步 akshare 调用做异步重试与超时控制."""
        last_exc = None
        for attempt in range(retries + 1):
            try:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, fn),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                last_exc = exc
                logger.warning("akshare %s 第 %d 次超时", name, attempt + 1)
            except Exception as exc:
                last_exc = exc
                logger.warning("akshare %s 第 %d 次失败: %s", name, attempt + 1, exc)
            if attempt < retries:
                wait = 0.5 * (2 ** attempt)
                logger.info("akshare %s 将在 %.1fs 后重试", name, wait)
                await asyncio.sleep(wait)
        raise last_exc or RuntimeError(f"akshare {name} 最终失败")

    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        try:
            import akshare as ak
        except ImportError:
            logger.info("akshare 未安装，跳过中国宏观数据采集")
            return {}

        # 抑制 akshare/pandas 进度条输出到控制台
        import pandas as pd
        pd.set_option("display.max_rows", None)
        try:
            from tqdm import tqdm
            tqdm.pandas(disable=True)
        except Exception:
            pass

        values: Dict[str, float] = {}
        failed: List[str] = []
        loop = asyncio.get_running_loop()

        async def index_drawdown(symbol: str, multiplier: float = 1.0):
            """获取 A 股指数日线并返回回撤风险分."""
            try:
                df = await AkShareFetcher._run_with_retry(
                    loop, lambda s=symbol: ak.stock_zh_index_daily(symbol=s), f"A股指数({symbol})"
                )
                if df is not None and not df.empty:
                    close = df["close"].dropna()
                    high1y = close.tail(252).max()
                    return round(_clamp((1 - close.iloc[-1] / high1y) * 100 * multiplier), 2)
            except Exception as exc:
                logger.warning("akshare A股指数 %s 最终失败: %s", symbol, exc)
                return None
            return None

        # 1) A 股核心指数：上证、沪深300、中证1000
        try:
            sh_dd = await index_drawdown("sh000001", 1.2)
            csi300_dd = await index_drawdown("sh000300", 1.2)
            csi1000_dd = await index_drawdown("sh000852", 1.0)
            dds = [d for d in [sh_dd, csi300_dd, csi1000_dd] if d is not None]
            if dds:
                values["china_equity"] = round(sum(dds) / len(dds), 2)
                values["capital_market"] = values["china_equity"]
            else:
                failed.append("A股指数")
        except Exception as exc:
            failed.append("A股指数")
            logger.warning("akshare A股指数抓取失败: %s", exc)

        # 2) 中国 10Y 国债收益率 -> china_credit（收益率越高风险越大）
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.bond_zh_us_rate(), "国债收益率")
            if df is not None and not df.empty:
                col = None
                for c in df.columns:
                    if "10" in str(c) and "中" in str(c):
                        col = c
                        break
                if col is None:
                    col = df.columns[-1]
                latest = float(df[col].dropna().iloc[-1])
                values["china_10y_yield"] = round(latest, 2)
                values["china_credit"] = round(_clamp((latest - 2.5) * 20 + 50), 2)
            else:
                failed.append("国债收益率")
        except Exception as exc:
            failed.append("国债收益率")
            logger.warning("akshare 国债收益率抓取最终失败: %s", exc)

        # 3) USD/CNY 汇率 -> china_fx（人民币贬值压力）
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.currency_boc_sina(), "USD/CNY")
            if df is not None and not df.empty:
                row = df[df.iloc[:, 0].astype(str).str.contains("美元")]
                if row.empty:
                    row = df[df.iloc[:, 0].astype(str).str.contains("USD", case=False)]
                if not row.empty:
                    rate = float(row.iloc[0, 5]) / 100
                    values["china_fx"] = round(_clamp((rate - 7.1) * 50 + 55), 2)
                else:
                    failed.append("USD/CNY")
            else:
                failed.append("USD/CNY")
        except Exception as exc:
            failed.append("USD/CNY")
            logger.warning("akshare USD/CNY 抓取最终失败: %s", exc)

        # 4) 国家统计局 70 城新建商品住宅价格指数同比 -> housing
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.macro_china_new_house_price(), "房价指数")
            if df is not None and not df.empty:
                yoy_cols = [c for c in df.columns if "同比" in str(c)]
                if yoy_cols:
                    yoy_values = pd.to_numeric(df[yoy_cols[0]], errors="coerce").dropna()
                    if not yoy_values.empty:
                        avg_yoy = float(yoy_values.mean())
                        values["housing"] = round(_clamp(50 - avg_yoy * 10), 2)
                    else:
                        failed.append("房价指数")
                else:
                    failed.append("房价指数")
            else:
                failed.append("房价指数")
        except Exception as exc:
            failed.append("房价指数")
            logger.warning("akshare 房价指数抓取最终失败: %s", exc)

        # 5) 国家统计局城镇调查失业率 -> real_economy
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.macro_china_urban_unemployment(), "失业率")
            if df is not None and not df.empty:
                rate = float(pd.to_numeric(df.iloc[-1], errors="coerce").dropna().iloc[-1])
                values["real_economy"] = round(_clamp((rate - 5.0) * 20 + 50), 2)
            else:
                failed.append("失业率")
        except Exception as exc:
            failed.append("失业率")
            logger.warning("akshare 失业率抓取最终失败: %s", exc)

        # 6) 财政部地方政府债券发行余额增速 -> debt（代理）
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.macro_china_bond_public(), "地方债发行")
            if df is not None and not df.empty:
                amounts = pd.to_numeric(df.iloc[:, 1], errors="coerce").dropna()
                if len(amounts) >= 2:
                    mom = (amounts.iloc[-1] - amounts.iloc[-2]) / abs(amounts.iloc[-2])
                    values["debt"] = round(_clamp(50 + mom * 100), 2)
                else:
                    failed.append("地方债发行")
            else:
                failed.append("地方债发行")
        except Exception as exc:
            failed.append("地方债发行")
            logger.warning("akshare 地方债发行抓取最终失败: %s", exc)

        # 7) 央行 LPR -> bank（代理银行系统流动性压力）
        try:
            df = await AkShareFetcher._run_with_retry(loop, lambda: ak.macro_china_lpr(), "LPR")
            if df is not None and not df.empty:
                row = df.iloc[-1]
                lpr_5y = float(pd.to_numeric(row, errors="coerce").dropna().iloc[-1])
                # 以 4.2% 为中性基准，越低风险分越高
                values["bank"] = round(_clamp((4.2 - lpr_5y) * 30 + 50), 2)
            else:
                failed.append("LPR")
        except Exception as exc:
            failed.append("LPR")
            logger.warning("akshare LPR 抓取最终失败: %s", exc)

        if failed:
            logger.warning("akshare 本次失败指标: %s", ", ".join(failed))

        return _validate_values(values, self.name)


class FallbackFetcher(BaseFetcher):
    """当外部数据源不可用时，回退到最近一次真实快照，避免伪造波动."""

    name = "fallback"

    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        return {}

    async def fetch_missing(
        self, session: AsyncSession, already_fetched: Dict[str, float]
    ) -> Dict[str, float]:
        result = await session.execute(select(Indicator))
        indicators = result.scalars().all()

        values: Dict[str, float] = {}
        for ind in indicators:
            if ind.code in already_fetched:
                continue

            snap = await get_latest_snapshot(session, ind.id)
            if snap is not None:
                values[ind.code] = round(float(snap.value), 2)
            else:
                base = FALLBACK_BASES.get(ind.code, 50)
                values[ind.code] = round(base, 2)

        return values

