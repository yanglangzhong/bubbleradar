"""每日风控日报生成器.

用法:
    cd backend
    python -m scripts.daily_report

报告默认输出到桌面: 风控日报_YYYYMMDD.html
"""
import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 确保能导入 backend 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

# 单机环境使用项目目录下的 SQLite，所有数据都归纳在项目内
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{DATA_DIR.as_posix()}/bubbleradar.db")
os.environ.setdefault("SYNC_DATABASE_URL", f"sqlite:///{DATA_DIR.as_posix()}/bubbleradar.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from sqlalchemy import select, desc
from app.db.session import AsyncSessionLocal, async_engine
from app.models import Base, CompositeScore, NewsArticle
from app.crawler.runner import run_crawl
from app.services.calculator import get_latest_composite


def _score_color(score: float) -> tuple:
    if score >= 70:
        return ("#dc3545", "🔴 高风险")
    if score >= 40:
        return ("#fd7e14", "🟡 中风险")
    return ("#28a745", "🟢 低风险")


async def generate_report():
    report_time = datetime.now(timezone.utc)
    print(f"[{report_time.strftime('%Y-%m-%d %H:%M:%S')}] 开始生成风控日报...")

    # 1. 建表并初始化
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        from scripts.seed import seed
        await seed(session)

    # 2. 执行数据采集
    async with AsyncSessionLocal() as session:
        summary = await run_crawl(session)
        print(f"采集完成: 写入 {summary['created']} 条快照, 综合分 {summary['composite']['composite_score']}")

    # 3. 读取最新综合分
    async with AsyncSessionLocal() as session:
        composite = await get_latest_composite(session)
        ai = composite.ai_bubble_score
        china = composite.china_risk_score
        global_ = composite.global_risk_score
        overall = composite.composite_score

    # 4. 读取最新新闻（24 小时内）
    async with AsyncSessionLocal() as session:
        since = report_time - timedelta(hours=24)
        result = await session.execute(
            select(NewsArticle)
            .where(NewsArticle.published_at >= since)
            .order_by(desc(NewsArticle.published_at))
            .limit(10)
        )
        news_items = result.scalars().all()

    # 5. 生成 HTML 报告
    overall_color, overall_label = _score_color(overall)
    ai_color, _ = _score_color(ai)
    china_color, _ = _score_color(china)
    global_color, _ = _score_color(global_)

    news_html = ""
    if news_items:
        for item in news_items:
            ts = item.published_at.strftime("%m-%d %H:%M") if item.published_at else "未知"
            sentiment_label = "中性"
            if item.sentiment_score and item.sentiment_score > 0.2:
                sentiment_label = "正面"
            elif item.sentiment_score and item.sentiment_score < -0.2:
                sentiment_label = "负面"
            news_html += f"""
            <div class="news-item">
                <p class="news-title">{item.title or "无标题"}</p>
                <p class="news-meta">{item.source or "未知来源"} · {ts} · 情绪：{sentiment_label}</p>
            </div>
            """
    else:
        news_html = "<p>今日暂无新闻数据。</p>"

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>金融风控日报 {report_time.strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 24px; background: #f5f6f7; }}
        h1 {{ color: #1a1a1a; border-bottom: 3px solid #0066ff; padding-bottom: 12px; margin-bottom: 8px; }}
        .subtitle {{ color: #6c757d; margin-bottom: 24px; }}
        .overall {{ background: #fff; border-radius: 16px; padding: 32px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.06); margin-bottom: 24px; }}
        .score {{ font-size: 72px; font-weight: 800; line-height: 1; margin: 16px 0; }}
        .label {{ font-size: 18px; font-weight: 600; padding: 6px 16px; border-radius: 20px; display: inline-block; background: #e9ecef; }}
        .cards {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px; }}
        .card {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .card h3 {{ margin: 0 0 12px; color: #495057; font-size: 14px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .card .num {{ font-size: 36px; font-weight: 700; }}
        .section {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }}
        .section h2 {{ margin-top: 0; color: #1a1a1a; font-size: 18px; }}
        .news-item {{ border-left: 3px solid #0066ff; padding-left: 12px; margin: 14px 0; }}
        .news-title {{ font-weight: 500; margin: 0 0 4px; color: #212529; }}
        .news-meta {{ margin: 0; color: #868e96; font-size: 12px; }}
        .footer {{ text-align: center; color: #adb5bd; font-size: 12px; margin-top: 32px; }}
    </style>
</head>
<body>
    <h1>📊 金融风控日报</h1>
    <p class="subtitle">生成时间：{report_time.strftime('%Y-%m-%d %H:%M:%S')} UTC</p>

    <div class="overall">
        <div class="score" style="color: {overall_color};">{overall:.1f}</div>
        <span class="label" style="color: {overall_color}; background: {overall_color}15;">{overall_label}</span>
        <p style="color: #6c757d; margin-top: 16px;">综合风险评分（0-100，越高越危险）</p>
    </div>

    <div class="cards">
        <div class="card">
            <h3>🤖 AI 泡沫风险</h3>
            <div class="num" style="color: {ai_color};">{ai:.1f}</div>
        </div>
        <div class="card">
            <h3>🇨🇳 中国风险</h3>
            <div class="num" style="color: {china_color};">{china:.1f}</div>
        </div>
        <div class="card">
            <h3>🌍 全球风险</h3>
            <div class="num" style="color: {global_color};">{global_:.1f}</div>
        </div>
    </div>

    <div class="section">
        <h2>📰 最新市场动态（24 小时内）</h2>
        {news_html}
    </div>

    <p class="footer">数据来源：FRED · Alpha Vantage · AkShare · Yahoo Finance · RSS 新闻</p>
</body>
</html>"""

    # 报告路径：优先桌面，无权限则 fallback 到项目根目录或临时目录
    candidates = [
        Path.home() / "Desktop",
        Path.home() / "桌面",
        Path(__file__).parent.parent.parent / "reports",
        Path(tempfile.gettempdir()),
    ]
    report_path = None
    filename = f"风控日报_{report_time.strftime('%Y%m%d')}.html"
    for folder in candidates:
        if not folder.exists():
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except Exception:
                continue
        candidate = folder / filename
        try:
            candidate.write_text(html, encoding="utf-8")
            report_path = candidate
            break
        except Exception:
            continue

    if report_path is None:
        raise RuntimeError("无法写入报告文件，请检查目录权限")
    print(f"报告已保存：{report_path}")

    # 6. Windows 右下角弹窗通知
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"综合评分：{overall:.1f}（{overall_label}）\n文件已保存到桌面",
            "金融风控日报已生成",
            0x40,
        )
    except Exception:
        pass

    return report_path


if __name__ == "__main__":
    asyncio.run(generate_report())
