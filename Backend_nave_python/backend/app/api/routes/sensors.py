from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.state_store import state_store
from app.services.telemetry_processor import telemetry_processor

router = APIRouter(tags=['sensors'])


@router.get('/api/sensors/latest')
def get_latest_sensors() -> dict[str, object]:
    return state_store.snapshot()


@router.get('/api/sensors/history')
def get_sensor_history(
    type: str = Query(..., description='Tipo de sensor, ej. gas o proximity'),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(300, ge=1, le=2000),
) -> list[dict[str, object]]:
    return telemetry_processor.latest_sensor_history(type, hours=hours, limit=limit)


@router.get('/api/sensores/historial')
def get_chart_history(
    horas: int = Query(24, ge=1, le=168),
    bucket_minutos: int = Query(5, ge=1, le=60),
) -> list[dict[str, object]]:
    return telemetry_processor.chart_history(hours=horas, bucket_minutes=bucket_minutos)


@router.get('/api/sensores/latest')
def get_latest_sensors_es() -> dict[str, object]:
    return state_store.frontend_payload()
