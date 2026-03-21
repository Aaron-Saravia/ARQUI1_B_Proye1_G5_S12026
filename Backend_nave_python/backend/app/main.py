from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio

from app.api.routes.commands import router as commands_router
from app.api.routes.events import router as events_router
from app.api.routes.health import router as health_router
from app.api.routes.messages import router as messages_router
from app.api.routes.sensors import router as sensors_router
from app.api.routes.stats import router as stats_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.core.topics import MQTT_SUBSCRIPTIONS
from app.db.mongo import mongo
from app.services.mqtt_service import mqtt_service
from app.services.realtime import realtime_gateway
from app.services.state_store import state_store
from app.services.telemetry_processor import telemetry_processor

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    realtime_gateway.bind_loop(asyncio.get_running_loop())

    try:
        mongo.connect()
    except Exception as exc:
        if settings.allow_degraded_mode:
            logger.warning('MongoDB no disponible, iniciando en modo degradado: %s', exc)
        else:
            raise

    try:
        mqtt_service.connect(MQTT_SUBSCRIPTIONS, telemetry_processor.process_message)
    except Exception as exc:
        if settings.allow_degraded_mode:
            logger.warning('MQTT no disponible, iniciando en modo degradado: %s', exc)
        else:
            raise

    logger.info('Backend %s listo en modo %s', settings.app_name, settings.app_env)
    yield

    mqtt_service.disconnect()
    mongo.disconnect()


fastapi_app = FastAPI(title='Nave Espacial Backend Python', version='1.0.0', lifespan=lifespan)
fastapi_app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins or ['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

fastapi_app.include_router(health_router)
fastapi_app.include_router(sensors_router)
fastapi_app.include_router(events_router)
fastapi_app.include_router(messages_router)
fastapi_app.include_router(commands_router)
fastapi_app.include_router(stats_router)


@realtime_gateway.sio.event
async def connect(sid: str, environ: dict, auth: dict | None = None) -> None:  # pragma: no cover - evento runtime
    logger.info('Socket conectado: %s', sid)
    await realtime_gateway.emit('telemetria_actualizada', state_store.frontend_payload(), room=sid)
    await realtime_gateway.emit('state:update', {'state': state_store.snapshot()['systemState']}, room=sid)


@realtime_gateway.sio.event
async def disconnect(sid: str) -> None:  # pragma: no cover - evento runtime
    logger.info('Socket desconectado: %s', sid)


app = socketio.ASGIApp(realtime_gateway.sio, other_asgi_app=fastapi_app)
