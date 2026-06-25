from fastapi import Request, HTTPException
from app.core.config import get_settings

settings = get_settings()


async def verify_api_key(request: Request):
    """Optional API key verification. If API_KEY is set, all /api/ requests must include it."""
    if not settings.API_KEY:
        return  # No auth configured, allow all

    api_key = request.headers.get("X-API-Key")
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
