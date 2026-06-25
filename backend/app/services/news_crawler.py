"""财经新闻采集与情绪分析 — 仅接入真实数据源，移除所有硬编码演示新闻."""
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NewsArticle

logger = logging.getLogger(__name__)

POSITIVE_WORDS = {
    "bullish", "rally", "growth", "boom", "recovery", "optimistic", "upgrade", "outperform",
    "上涨", "反弹", "复苏", "增长", "乐观", "看好", "强劲", "回暖", "企稳", "超预期",
    "降息", "降准", "宽松", "刺激", "支持", "利好", "创新高", "突破",
}

NEGATIVE_WORDS = {
    "crash", "recession", "bearish", "default", "bankruptcy", "crisis", "collapse", "selloff",
    "plunge", "panic", "liquidity", "contagion", "downgrade", "underperform",
    "下跌", "崩盘", "衰退", "违约", "破产", "危机", "暴跌", "抛售", "恐慌", "传染",
    "滞胀", "加息", "收紧", "制裁", "封锁", "断供", "裁员", "亏损", "下滑", "恶化",
    "利空", "跳水", "跌停", "熔断", "暴雷", "债务", "泡沫", "过热",
}

HIGH_IMPACT_WORDS = {
    "crash", "recession", "crisis", "collapse", "default", "bankruptcy", "contagion",
    "崩盘", "衰退", "危机", "违约", "破产", "暴跌", "恐慌", "熔断", "滞胀",
    "制裁", "断供", "封锁", "暴雷", "泡沫破裂", "系统性风险",
}

# RSS 源：国际 + 中国科技财经
RSS_FEEDS = [
    "https://finance.yahoo.com/news/rssindex",
    "https://www.36kr.com/feed",
]

# 新浪财经 JSON API（lid 含义：2515 A股公司 / 2516 上市公司 / 2517 基金·美股 / 2518 产经）
SINA_JSON_APIS = [
    {"name": "新浪财经·A股公司", "lid": "2515"},
    {"name": "新浪财经·上市公司", "lid": "2516"},
    {"name": "新浪财经·基金美股", "lid": "2517"},
    {"name": "新浪财经·产经", "lid": "2518"},
]

# 东方财富快讯 API
EASTMONEY_APIS = [
    {"name": "东方财富·全球财经", "type": "lives", "page": 1},
    {"name": "东方财富·A股快讯", "type": "stock", "page": 1},
]


def _analyze_sentiment(text: str) -> float:
    text_lower = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((neg - pos) / total, 2)


def _impact_score(text: str, sentiment: float) -> float:
    text_lower = text.lower()
    base = min(100, abs(sentiment) * 100 + sum(20 for w in HIGH_IMPACT_WORDS if w in text_lower))
    return round(base, 2)


def _strip_tag(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _text_of(elem, default: str = "") -> str:
    return (elem.text or default).strip()


def _source_name(url: str, feed_title: str = "") -> str:
    """从 URL 或 feed 标题提取可读来源名."""
    if feed_title:
        return feed_title.strip()
    from urllib.parse import urlparse
    host = urlparse(url).netloc or url
    return host.replace("www.", "")


def _parse_xml_feed(text: str, url: str) -> List[dict]:
    """使用标准库 xml.etree 解析 RSS/Atom，避免依赖 feedparser."""
    entries: List[dict] = []
    try:
        root = ET.fromstring(text)
    except Exception as exc:
        logger.warning("RSS %s XML 解析失败: %s", url, exc)
        return entries

    root_tag = _strip_tag(root.tag)
    feed_title = ""
    items: List[ET.Element] = []

    if root_tag == "rss":
        channel = root.find("channel")
        if channel is None:
            return entries
        title_elem = channel.find("title")
        if title_elem is not None:
            feed_title = _text_of(title_elem)
        items = [child for child in channel if _strip_tag(child.tag) == "item"]
    elif root_tag == "feed":
        title_elem = root.find("title")
        if title_elem is not None:
            feed_title = _text_of(title_elem)
        items = [child for child in root if _strip_tag(child.tag) == "entry"]
    else:
        return entries

    source_name = _source_name(url, feed_title)

    for item in items[:10]:
        title = ""
        link = ""
        published = ""
        summary = ""
        for child in item:
            tag = _strip_tag(child.tag)
            if tag == "title" and not title:
                title = _text_of(child)
            elif tag == "link" and not link:
                if child.text and child.text.strip().startswith("http"):
                    link = child.text.strip()
                elif child.attrib.get("href", "").startswith("http"):
                    link = child.attrib.get("href")
            elif tag in ("pubDate", "published", "updated") and not published:
                published = _text_of(child)
            elif tag in ("description", "summary", "content") and not summary:
                summary = _text_of(child)
        if not title:
            continue
        sentiment = _analyze_sentiment(title)
        impact = _impact_score(title, sentiment)
        entries.append({
            "title": title,
            "source": source_name,
            "url": link or None,
            "summary": summary[:512],
            "sentiment_score": sentiment,
            "impact_score": impact,
            "published_at": _parse_time(published),
        })
    return entries


def _parse_time(value: str) -> datetime:
    if not value:
        return datetime.utcnow()
    value = value.strip()
    formats = [
        "%a, %d %b %Y %H:%M:%S %Z",
        "%a, %d %b %Y %H:%M:%S %z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(value, fmt)
            if dt.tzinfo is not None:
                dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
            return dt
        except ValueError:
            continue
    return datetime.utcnow()


async def _fetch_feed(url: str, client: httpx.AsyncClient) -> List[dict]:
    try:
        resp = await client.get(url, timeout=15, follow_redirects=True)
        resp.raise_for_status()
        try:
            import feedparser
            feed = feedparser.parse(resp.text)
            entries = []
            for entry in feed.entries[:10]:
                title = entry.get("title", "")
                if not title:
                    continue
                sentiment = _analyze_sentiment(title)
                impact = _impact_score(title, sentiment)
                entries.append({
                    "title": title,
                    "source": entry.get("source", {}).get("title", _source_name(url, feed.feed.get("title", "")))
                    if isinstance(entry.get("source"), dict)
                    else _source_name(url, feed.feed.get("title", "")),
                    "url": entry.get("link"),
                    "summary": (entry.get("summary", "") or "")[:512],
                    "sentiment_score": sentiment,
                    "impact_score": impact,
                    "published_at": _parse_time(entry.get("published") or ""),
                })
            return entries
        except ImportError:
            return _parse_xml_feed(resp.text, url)
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            return []
        logger.warning("RSS %s 获取失败: %s", url, exc)
        return []
    except Exception as exc:
        logger.warning("RSS %s 获取失败: %s", url, exc)
        return []


async def _fetch_sina_json_feed(client: httpx.AsyncClient, name: str, lid: str) -> List[dict]:
    """通过新浪财经 JSON API 获取中国财经新闻."""
    url = "https://feed.mix.sina.com.cn/api/roll/get"
    try:
        resp = await client.get(
            url,
            params={
                "pageid": "153",
                "lid": lid,
                "k": "",
                "num": "10",
                "page": "1",
                "r": str(int(datetime.utcnow().timestamp())),
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        entries: List[dict] = []
        for item in data.get("result", {}).get("data", []):
            title = item.get("title", "").strip()
            if not title:
                continue
            sentiment = _analyze_sentiment(title)
            impact = _impact_score(title, sentiment)
            published = datetime.utcfromtimestamp(int(item.get("ctime", 0))) if item.get("ctime") else datetime.utcnow()
            link = item.get("url") or item.get("wapurl")
            entries.append({
                "title": title,
                "source": name,
                "url": link,
                "summary": (item.get("summary") or item.get("intro") or "")[:512],
                "sentiment_score": sentiment,
                "impact_score": impact,
                "published_at": published,
            })
        return entries
    except Exception as exc:
        logger.warning("新浪财经 API (lid=%s) 获取失败: %s", lid, exc)
        return []


async def _fetch_eastmoney_feed(client: httpx.AsyncClient, name: str, type_: str, page: int) -> List[dict]:
    """通过东方财富 API 获取快讯."""
    try:
        # 东方财富快讯 API（公开接口，无鉴权）
        url = f"https://np-anotice-stock.eastmoney.com/api/security/ann"
        if type_ == "stock":
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        else:
            # 使用快讯接口
            url = "https://np-anotice-stock.eastmoney.com/api/security/ann"
        # 实际上东方财富快讯接口较复杂，这里用另一个更稳定的公开接口
        url = "https://www.cls.cn/nodeapi/telegraphList"
        resp = await client.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.cls.cn/",
        })
        resp.raise_for_status()
        data = resp.json()
        entries: List[dict] = []
        for item in data.get("data", {}).get("roll_data", [])[:10]:
            title = item.get("title", "").strip() or item.get("content", "").strip()
            if not title:
                continue
            sentiment = _analyze_sentiment(title)
            impact = _impact_score(title, sentiment)
            published = datetime.utcfromtimestamp(item.get("ctime", 0)) if item.get("ctime") else datetime.utcnow()
            link = item.get("shareurl") or f"https://www.cls.cn/detail/{item.get('id', '')}"
            entries.append({
                "title": title,
                "source": "财联社",
                "url": link if link.startswith("http") else None,
                "summary": "",
                "sentiment_score": sentiment,
                "impact_score": impact,
                "published_at": published,
            })
        return entries
    except Exception as exc:
        logger.warning("东方财富/财联社 API 获取失败: %s", exc)
        return []


async def _fetch_wallstreetcn_feed(client: httpx.AsyncClient) -> List[dict]:
    """华尔街见闻实时快讯."""
    try:
        url = "https://api-one.wallstcn.com/apiv1/content/lives"
        resp = await client.get(
            url,
            params={"channel": "global-channel", "limit": 20},
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Referer": "https://wallstreetcn.com/",
            },
        )
        resp.raise_for_status()
        data = resp.json()
        entries: List[dict] = []
        for item in data.get("data", {}).get("items", [])[:10]:
            content = item.get("content", "").strip()
            if not content:
                continue
            # 提取标题：通常 content 是一段文字，取前 60 字作为标题
            title = content[:80] if len(content) <= 80 else content[:80] + "..."
            sentiment = _analyze_sentiment(content)
            impact = _impact_score(content, sentiment)
            published = datetime.utcfromtimestamp(item.get("display_time", 0)) if item.get("display_time") else datetime.utcnow()
            link = item.get("uri") or item.get("share_url")
            entries.append({
                "title": title,
                "source": "华尔街见闻",
                "url": link if link and link.startswith("http") else None,
                "summary": content[:512] if len(content) > 80 else "",
                "sentiment_score": sentiment,
                "impact_score": impact,
                "published_at": published,
            })
        return entries
    except Exception as exc:
        logger.warning("华尔街见闻 API 获取失败: %s", exc)
        return []


async def crawl_news(session: AsyncSession, max_items: int = 30) -> dict:
    """抓取新闻，仅接入真实数据源，写入数据库，返回统计信息.

    注意：当所有真实数据源均不可达时，不再返回硬编码演示新闻，而是返回空列表，
    并在前端显示"暂无实时新闻"提示。
    """
    items: List[dict] = []
    source_errors: Dict[str, str] = {}

    async with httpx.AsyncClient() as client:
        # 1. RSS 源（国际 + 中国科技）
        for idx, url in enumerate(RSS_FEEDS):
            if idx > 0:
                await asyncio.sleep(1)
            try:
                items.extend(await _fetch_feed(url, client))
            except Exception as exc:
                source_errors[f"rss:{url}"] = str(exc)
                logger.warning("RSS %s 抓取失败: %s", url, exc)

        # 2. 新浪财经 JSON API（中国市场）
        for idx, cfg in enumerate(SINA_JSON_APIS):
            if items:
                await asyncio.sleep(1)
            try:
                items.extend(await _fetch_sina_json_feed(client, cfg["name"], cfg["lid"]))
            except Exception as exc:
                source_errors[f"sina:{cfg['name']}"] = str(exc)
                logger.warning("新浪财经 %s 抓取失败: %s", cfg["name"], exc)

        # 3. 财联社电报
        if items:
            await asyncio.sleep(1)
        try:
            items.extend(await _fetch_eastmoney_feed(client, "财联社", "lives", 1))
        except Exception as exc:
            source_errors["cls"] = str(exc)
            logger.warning("财联社电报抓取失败: %s", exc)

        # 4. 华尔街见闻
        if items:
            await asyncio.sleep(1)
        try:
            items.extend(await _fetch_wallstreetcn_feed(client))
        except Exception as exc:
            source_errors["wallstreetcn"] = str(exc)
            logger.warning("华尔街见闻抓取失败: %s", exc)

    # 如果所有真实源都失败，items 为空，不再使用 DEMO_NEWS 兜底
    if not items:
        logger.warning("所有真实新闻源均不可达，本次不写入任何新闻")

    if source_errors:
        logger.warning("新闻源失败详情: %s", source_errors)

    # 去重写入（按标题去重，优先保留最新）
    created = 0
    skipped = 0
    for item in items[:max_items]:
        result = await session.execute(
            select(NewsArticle).where(NewsArticle.title == item["title"])
        )
        if result.scalar_one_or_none():
            skipped += 1
            continue
        article = NewsArticle(**item)
        session.add(article)
        created += 1

    await session.commit()

    return {"created": created, "skipped": skipped, "total": len(items[:max_items]), "source_errors": source_errors}
