from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.mongo import mongo
from app.services.command_service import command_service
from app.services.telemetry_processor import telemetry_processor

router = APIRouter(tags=['messages'])


class MessageBody(BaseModel):
    text: str = Field(min_length=1, max_length=64)


@router.get('/api/messages')
def get_messages(limit: int = Query(10, ge=1, le=200)) -> list[dict[str, object]]:
    if not mongo.is_connected:
        return []
    cursor = mongo.collection('messages').find().sort('timestamp', -1).limit(limit)
    return [telemetry_processor.serialize_document(doc) for doc in cursor]


@router.post('/api/messages', status_code=201)
def post_message(body: MessageBody) -> dict[str, object]:
    text = body.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail='El mensaje no puede ir vacío.')
    return command_service.save_message(text)
