import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import desc, select

from app.api import api_router
from app.api.ws import router as ws_router, broadcast_dashboard_update
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.crawler import start_scheduler, stop_scheduler
from app.crawler.runner import run_crawl
from app.db.session import AsyncSessionLocal, async_engine
from app.models import NewsArticle
from app.services.calculator import calculate_composite_score, _resolve_composite_source
from app.services.scoring import calculate_category_score
from app.services.insight import generate_insight
from app.core.security import get_password_hash
from app.models import User
from scripts.seed import seed_events

settings = get_settings()
configure_logging(json_format=settings.ENVIRONMENT == "production")
logger = get_logger(__name__)

# 全局缓存：启动时/latest/refresh后的最新分析结果
_latest_analysis: dict = {
    "status": "pending",  # pending / running / ready / error
    "message": "系统启动中，数据准备中，请稍候...",
    "scores": {"ai_bubble": 0.0, "china_risk": 0.0, "global_risk": 0.0, "crypto_risk": 0.0},
    "composite": {
        "ai_bubble_score": 0.0,
        "china_risk_score": 0.0,
        "global_risk_score": 0.0,
        "crypto_risk_score": 0.0,
        "composite_score": 0.0,
        "timestamp": None,
        "source": None,
    },
    "news": [],
    "timestamp": None,
    "source_errors": {},
}


def _print_analysis_summary():
    """在控制台打印启动时的分析摘要."""
    data = _latest_analysis
    status = data.get("status")
    if status != "ready":
        print(f"[分析摘要] 状态: {status} | 消息: {data.get('message')}")
        return

    scores = data.get("scores", {})
    composite = data.get("composite", {})
    news = data.get("news", [])

    print(
        f"[分析摘要] 综合风险分: {composite.get('composite_score', 0.0):.2f} | "
        f"AI泡沫: {scores.get('ai_bubble', 0.0):.2f} | "
        f"中国: {scores.get('china_risk', 0.0):.2f} | "
        f"全球: {scores.get('global_risk', 0.0):.2f} | "
        f"加密: {scores.get('crypto_risk', 0.0):.2f} | "
        f"新闻: {len(news)} | 时间: {data.get('timestamp')}"
    )


async def _fetch_latest_news(session):
    """从数据库读取最近 7 天新闻，避免展示过期存档."""
    from datetime import timedelta
    since = datetime.utcnow() - timedelta(days=7)
    result = await session.execute(
        select(NewsArticle)
        .where(NewsArticle.published_at >= since)
        .order_by(desc(NewsArticle.published_at))
        .limit(20)
    )
    articles = result.scalars().all()
    return [
        {
            "id": article.id,
            "title": article.title,
            "source": article.source or "RSS",
            "url": article.url,
            "sentiment_score": article.sentiment_score,
            "impact_score": article.impact_score,
            "published_at": article.published_at.isoformat() if article.published_at else None,
        }
        for article in articles
    ]


async def _run_analysis():
    """执行一次完整的数据采集、评分与新闻抓取，并缓存结果."""
    global _latest_analysis

    _latest_analysis.update(
        {
            "status": "running",
            "message": "正在采集数据并计算风险评分，请稍候...",
            "timestamp": datetime.utcnow().isoformat(),
            "source_errors": {},
        }
    )

    async with AsyncSessionLocal() as session:
        try:
            # 1. 数据采集：runner 内部已对每个 fetcher 做错误隔离
            crawl_summary = await run_crawl(session)
            _latest_analysis["source_errors"] = crawl_summary.get("source_errors", {})
        except Exception as exc:
            logger.exception("启动数据采集失败: %s", exc)
            crawl_summary = {
                "created": 0,
                "skipped": 0,
                "fetched": 0,
                "composite": None,
                "alerts": 0,
                "news": {"created": 0, "skipped": 0, "total": 0},
                "source_errors": {"crawler": str(exc)},
            }
            _latest_analysis["source_errors"] = crawl_summary["source_errors"]

        # 2. 计算风险评分（分项）
        scores = {}
        for category, key in (("ai", "ai_bubble"), ("china", "china_risk"), ("global", "global_risk"), ("crypto", "crypto_risk")):
            try:
                scores[key] = await calculate_category_score(session, category)
            except Exception as exc:
                logger.warning("%s 风险评分计算失败: %s", category, exc)
                scores[key] = 0.0

        # 3. 计算综合指标
        try:
            composite_obj = await calculate_composite_score(session)
            source = getattr(composite_obj, "source", None) or await _resolve_composite_source(session)
            composite = {
                "ai_bubble_score": composite_obj.ai_bubble_score,
                "china_risk_score": composite_obj.china_risk_score,
                "global_risk_score": composite_obj.global_risk_score,
                "crypto_risk_score": composite_obj.crypto_risk_score,
                "composite_score": composite_obj.composite_score,
                "timestamp": composite_obj.timestamp.isoformat() if composite_obj.timestamp else None,
                "source": source,
            }
        except Exception as exc:
            logger.warning("综合指标计算失败: %s", exc)
            composite = crawl_summary.get("composite") or {
                "ai_bubble_score": 0.0,
                "china_risk_score": 0.0,
                "global_risk_score": 0.0,
                "crypto_risk_score": 0.0,
                "composite_score": 0.0,
                "timestamp": None,
            }
            composite.setdefault("source", await _resolve_composite_source(session))

        # 4. 读取最新新闻列表（run_crawl 已抓取并写入数据库）
        try:
            news = await _fetch_latest_news(session)
        except Exception as exc:
            logger.warning("读取新闻失败: %s", exc)
            news = []

    _latest_analysis.update(
        {
            "status": "ready",
            "message": "数据已就绪",
            "scores": {
                "ai_bubble": round(scores.get("ai_bubble", 0.0), 2),
                "china_risk": round(scores.get("china_risk", 0.0), 2),
                "global_risk": round(scores.get("global_risk", 0.0), 2),
                "crypto_risk": round(scores.get("crypto_risk", 0.0), 2),
            },
            "composite": composite,
            "news": news,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )

    # 分析完成后通过 WebSocket 即时推送最新仪表盘数据
    try:
        await broadcast_dashboard_update()
    except Exception as exc:
        logger.warning("WebSocket 广播失败: %s", exc)


def _persist_analysis_error(exc: Exception):
    """将分析失败信息追加到日志文件，避免重启后丢失."""
    log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "logs"))
    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "analysis_errors.log")
    timestamp = datetime.utcnow().isoformat()
    try:
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] 分析失败: {exc}\n")
    except Exception as write_exc:
        logger.warning("无法写入分析错误日志: %s", write_exc)


async def _run_analysis_task():
    """后台执行启动分析，避免阻塞服务启动."""
    try:
        await _run_analysis()
        _print_analysis_summary()
    except Exception as exc:
        logger.exception("后台启动分析失败: %s", exc)
        _persist_analysis_error(exc)
        _latest_analysis.update(
            {
                "status": "error",
                "message": f"数据分析失败: {exc}",
                "timestamp": datetime.utcnow().isoformat(),
            }
        )


async def _seed_events_on_startup():
    """启动时如果历史事件表为空，则自动写入内置事件."""
    try:
        async with AsyncSessionLocal() as session:
            await seed_events(session)
            await session.commit()
    except Exception as exc:
        logger.warning("启动时事件 seed 失败: %s", exc)


def _run_alembic_upgrade_sync():
    """在线程中执行 Alembic upgrade head（避免与 lifespan 事件循环冲突）."""
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine
    from app.models import Base

    alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        # 兼容遗留数据库：若表已存在但无 alembic_version，清理后重建（仅开发环境）
        if settings.ENVIRONMENT != "development":
            raise

        sync_url = settings.SYNC_DATABASE_URL
        if sync_url.startswith("sqlite"):
            engine = create_engine(sync_url)
            try:
                Base.metadata.drop_all(engine)
            finally:
                engine.dispose()
            command.upgrade(alembic_cfg, "head")
        else:
            raise


async def _run_alembic_upgrade():
    """启动时自动执行 Alembic upgrade head 以管理表结构."""
    try:
        await asyncio.to_thread(_run_alembic_upgrade_sync)
        logger.info("Alembic 迁移已执行到最新版本")
    except Exception as exc:
        logger.warning("Alembic 迁移执行失败: %s", exc)


async def _create_default_user():
    """如果数据库中没有任何用户，则创建默认管理员账号."""
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import func
            result = await session.execute(select(func.count(User.id)))
            count = result.scalar() or 0
            if count == 0:
                user = User(
                    email="admin@example.com",
                    hashed_password=get_password_hash("admin"),
                    is_active=True,
                    is_superuser=True,
                )
                session.add(user)
                await session.commit()
                logger.info("已创建默认管理员账号: admin@example.com / admin")
    except Exception as exc:
        logger.warning("创建默认用户失败: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: 使用 Alembic 管理表结构，替代 Base.metadata.create_all
    await _run_alembic_upgrade()

    # 启动时自动填充历史事件（幂等）
    await _seed_events_on_startup()

    # 启动时创建默认管理员（仅在用户表为空时）
    await _create_default_user()

    # 启动引导：检查 .env 文件是否存在
    backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    env_path = os.path.join(backend_dir, ".env")
    env_example_path = os.path.join(backend_dir, ".env.example")
    if not os.path.exists(env_path) and os.path.exists(env_example_path):
        print("\n" + "=" * 60)
        print("[INFO] 检测到 backend/.env 不存在")
        print("       首次使用请执行：copy backend/.env.example backend/.env")
        print("       然后编辑 backend/.env 填入 FRED / Alpha Vantage API 密钥")
        print("=" * 60 + "\n")

    # 启动引导：关键 API 密钥检查
    if not settings.FRED_API_KEY or settings.FRED_API_KEY in ("your-fred-api-key", ""):
        print("\n" + "=" * 60)
        print("[WARN] FRED_API_KEY 未配置或仍为占位符")
        print("       美债收益率、信用利差、美元指数等官方指标将跳过")
        print("       请复制 backend/.env.example 为 backend/.env 并填入真实密钥")
        print("=" * 60 + "\n")
    if not settings.ALPHA_VANTAGE_API_KEY or settings.ALPHA_VANTAGE_API_KEY in ("your-alphavantage-api-key", ""):
        print("\n" + "=" * 60)
        print("[WARN] ALPHA_VANTAGE_API_KEY 未配置或仍为占位符")
        print("       USD/CNY、NVDA/SPY 实时报价等备份指标将跳过")
        print("       请复制 backend/.env.example 为 backend/.env 并填入真实密钥")
        print("=" * 60 + "\n")

    # 启动时自动执行一次完整分析，放在后台任务中避免阻塞服务启动
    asyncio.create_task(_run_analysis_task())

    # 默认 backend 容器不启动调度器，由独立 scheduler 服务负责，避免重复采集
    if os.environ.get("ENABLE_SCHEDULER", "false").lower() == "true":
        start_scheduler()
    try:
        yield
    finally:
        if os.environ.get("ENABLE_SCHEDULER", "false").lower() == "true":
            stop_scheduler()


# API 限流：基于客户端 IP，默认 60 次/分钟，公开端点更严格
limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API key authentication for /api/ routes. /health is always public."""
    if settings.API_KEY and request.url.path.startswith("/api/"):
        api_key = request.headers.get("X-API-Key")
        if not api_key or api_key != settings.API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key"},
            )
    response = await call_next(request)
    return response


app.include_router(ws_router)
app.include_router(api_router, prefix="/api")


@app.get("/health")
@limiter.limit("30/minute")
async def health_check(request: Request):
    return {"status": "ok", "version": settings.VERSION}


@app.get("/api/analysis")
@limiter.limit("30/minute")
async def get_analysis(request: Request):
    """返回启动时的最新分析结果（包含状态信息）."""
    return _latest_analysis


@app.post("/api/analysis/refresh")
@limiter.limit("5/minute")
async def refresh_analysis(request: Request):
    """手动重新触发爬取+分析，并返回最新结果."""
    await _run_analysis()
    return _latest_analysis


@app.get("/api/analysis/insight")
@limiter.limit("30/minute")
async def get_analysis_insight(request: Request):
    """基于当前风险分数与新闻生成 AI 智能解读."""
    scores = _latest_analysis.get("scores", {})
    news = _latest_analysis.get("news", [])
    composite = _latest_analysis.get("composite", {})
    composite_score = composite.get("composite_score") if composite else None
    return await generate_insight(scores, news, composite_score)
