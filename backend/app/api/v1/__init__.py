from fastapi import APIRouter
from .indicators import router as indicators_router
from .composite import router as composite_router
from .alerts import router as alerts_router
from .news import router as news_router
from .crawler import router as crawler_router
from .analytics import router as analytics_router
from .dashboard import router as dashboard_router
from .auth import router as auth_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router)
router.include_router(indicators_router)
router.include_router(composite_router)
router.include_router(alerts_router)
router.include_router(news_router)
router.include_router(crawler_router)
router.include_router(analytics_router)
router.include_router(dashboard_router)
