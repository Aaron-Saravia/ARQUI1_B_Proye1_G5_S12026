from __future__ import annotations

import asyncio
import logging
from typing import Any

import socketio

logger = logging.getLogger(__name__)


class RealtimeGateway:
    def __init__(self) -> None:
        self.loop: asyncio.AbstractEventLoop | None = None
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop

    async def emit(self, event_name: str, payload: Any, room: str | None = None) -> None:
        await self.sio.emit(event_name, payload, room=room)

    def emit_sync(self, event_name: str, payload: Any, room: str | None = None) -> None:
        if self.loop is None or not self.loop.is_running():
            logger.debug('No hay loop disponible para emitir %s', event_name)
            return
        asyncio.run_coroutine_threadsafe(self.emit(event_name, payload, room=room), self.loop)


realtime_gateway = RealtimeGateway()
