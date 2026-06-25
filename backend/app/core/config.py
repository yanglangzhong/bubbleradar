from typing import Any

from pydantic_settings import BaseSettings
from functools import lru_cache


def _parse_cors_origins(value: Any) -> list[str]:
    """兼容 list、JSON 列表与逗号分隔字符串的 CORS 配置."""
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned.startswith("[") and cleaned.endswith("]"):
            cleaned = cleaned[1:-1]
        return [part.strip().strip('"').strip("'") for part in cleaned.split(",") if part.strip()]
    return []


class Settings(BaseSettings):
    PROJECT_NAME: str = "BubbleRadar API"
    VERSION: str = "3.0.0"
    DESCRIPTION: str = "AI泡沫与中国经济风险实时监控系统"
    ENVIRONMENT: str = "development"

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/bubbleradar"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@db:5432/bubbleradar"

    REDIS_URL: str = "redis://redis:6379/0"

    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    FRED_API_KEY: str = ""
    ALPHA_VANTAGE_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    API_KEY: str = ""

    # 告警推送配置（留空则跳过该渠道）
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    ALERT_EMAIL_TO: str = ""  # 多个用逗号分隔

    SERVERCHAN_SENDKEY: str = ""  # Server酱 sendkey
    WECHAT_WORK_WEBHOOK: str = ""  # 企业微信机器人 webhook URL

    # 可观测性（可选）
    SENTRY_DSN: str = ""  # Sentry DSN，留空则禁用

    @property
    def cors_origins(self) -> list[str]:
        return _parse_cors_origins(self.CORS_ORIGINS)

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
