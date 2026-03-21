from __future__ import annotations

from fastapi import APIRouter, Query

from app.db.mongo import mongo
from app.services.telemetry_processor import telemetry_processor

router = APIRouter(tags=['events'])


@router.get('/api/events')
def get_events(limit: int = Query(20, ge=1, le=200)) -> list[dict[str, object]]:
    if not mongo.is_connected:
        return []
    cursor = mongo.collection('events').find().sort('timestamp', -1).limit(limit)
    return [telemetry_processor.serialize_document(doc) for doc in cursor]
