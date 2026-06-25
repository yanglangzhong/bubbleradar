"""WebSocket 实时推送：分析完成后即时广播最新仪表盘数据."""
import asyncio
import json
import logging
from typing import List, Set

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import AsyncSessionLocal
from app.api.v1.dashboard import build_dashboard_data

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class DashboardConnectionManager:
    """管理 /ws/dashboard 的客户端连接，支持广播与断线清理."""

    def __init__(self):
        self._connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self._connections.add(websocket)
        logger.info("WebSocket 客户端已连接，当前连接数: %d", len(self._connections))

    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            self._connections.discard(websocket)
        logger.info("WebSocket 客户端已断开，当前连接数: %d", len(self._connections))

    @property
    def active_connections(self) -> List[WebSocket]:
        return list(self._connections)

    async def broadcast(self, message: dict):
        """向所有已连接客户端广播 JSON 消息，失败时仅记录日志不中断其他连接."""
        payload = json.dumps(message, default=str)
        dead: List[WebSocket] = []
        for conn in self.active_connections:
            try:
                await conn.send_text(payload)
            except Exception as exc:
                logger.warning("WebSocket 广播失败: %s", exc)
                dead.append(conn)
        if dead:
            async with self._lock:
                for conn in dead:
                    self._connections.discard(conn)


manager = DashboardConnectionManager()


@router.websocket("/ws/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """仪表盘实时数据流。

    连接建立后立即推送一次当前仪表盘快照；后续服务端在每次分析完成后主动广播更新。
    客户端可通过发送 ping 维持连接，服务端返回 pong。
    """
    await manager.connect(websocket)

    # 连接成功后立即推送一次快照
    try:
        async with AsyncSessionLocal() as session:
            snapshot = await build_dashboard_data(session)
        await websocket.send_json({"type": "snapshot", "data": snapshot})
    except Exception as exc:
        logger.warning("WebSocket 初始快照发送失败: %s", exc)
        await manager.disconnect(websocket)
        return

    try:
        while True:
            data = await websocket.receive_text()
            if data.strip() == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as exc:
        logger.warning("WebSocket 连接异常: %s", exc)
        await manager.disconnect(websocket)


async def broadcast_dashboard_update(session: AsyncSession | None = None):
    """供分析任务在完成时调用，广播最新仪表盘数据到所有客户端."""
    close_session = False
    if session is None:
        session = AsyncSessionLocal()
        close_session = True
    try:
        snapshot = await build_dashboard_data(session)
        await manager.broadcast({"type": "update", "data": snapshot})
    except Exception as exc:
        logger.warning("WebSocket 广播仪表盘更新失败: %s", exc)
    finally:
        if close_session:
            await session.close()
