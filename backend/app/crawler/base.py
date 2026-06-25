"""采集器基类."""
from abc import ABC, abstractmethod
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession


class BaseFetcher(ABC):
    """所有数据抓取器的抽象基类."""

    name: str = ""

    @abstractmethod
    async def fetch(self, session: AsyncSession) -> Dict[str, float]:
        """抓取数据，返回 {indicator_code: value}."""
        ...
