from __future__ import annotations

from fastapi import APIRouter

from app.db.mongo import mongo
from app.services.mqtt_service import mqtt_service

router = APIRouter(prefix='/api/health', tags=['health'])


@router.get('')
def health_check() -> dict[str, object]:
    return {
        'ok': True,
        'service': 'nave-backend-python',
        'mongoConnected': mongo.is_connected,
        'mqttConnected': mqtt_service.connected,
    }
