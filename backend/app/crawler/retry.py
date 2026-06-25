"""通用异步重试工具."""
import asyncio
import logging
from functools import wraps
from typing import Callable, Optional, Tuple, Type

logger = logging.getLogger(__name__)


def async_retry(
    retries: int = 2,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """装饰异步函数，在指定异常时按指数退避重试.

    Args:
        retries: 最大重试次数（不含首次）.
        delay: 首次重试等待秒数.
        backoff: 退避系数.
        exceptions: 需要重试的异常类型.
        on_retry: 每次重试前的回调，参数为 (异常, 尝试次数).
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            wait = delay
            for attempt in range(retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as exc:
                    last_exc = exc
                    if attempt >= retries:
                        break
                    if on_retry:
                        try:
                            on_retry(exc, attempt + 1)
                        except Exception:
                            pass
                    logger.warning(
                        "%s 第 %d 次失败，%.1fs 后重试: %s",
                        func.__name__,
                        attempt + 1,
                        wait,
                        exc,
                    )
                    await asyncio.sleep(wait)
                    wait *= backoff
            raise last_exc or RuntimeError(f"{func.__name__} 最终失败")

        return wrapper

    return decorator
