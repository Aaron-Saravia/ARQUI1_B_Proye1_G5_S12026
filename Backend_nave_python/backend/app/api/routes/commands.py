from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.command_service import command_service

router = APIRouter(tags=['commands'])


class CommandBody(BaseModel):
    actuator: str | None = None
    action: str | None = None
    value: Any = None
    comando: str | None = None
    valor: Any = None


class CommandTranslator:
    @staticmethod
    def normalize(body: CommandBody) -> tuple[str, str, Any, bool]:
        if body.actuator and body.action:
            return body.actuator.strip(), body.action.strip(), body.value, False

        comando = (body.comando or '').strip().lower()
        valor = body.valor
        if not comando:
            raise ValueError('Debes enviar actuator/action o comando/valor.')

        if comando == 'torreta':
            return 'torreta', 'set-angle', int(valor or 0), False
        if comando == 'compuerta':
            action = 'open' if str(valor).strip().lower() in {'abrir', 'open', 'abierta'} else 'close'
            return 'compuertas', action, valor, False
        if comando == 'camuflaje':
            action = 'activate' if str(valor).strip().lower() in {'activar', 'activate', 'on', 'true'} else 'deactivate'
            return 'camuflaje', action, valor, False
        if comando == 'lcd':
            return 'lcd', 'send-text', str(valor or ''), True
        if comando == 'emergencia':
            return 'emergencia', 'stop-all', valor, False
        raise ValueError(f'Comando no soportado: {comando}')


@router.post('/api/commands', status_code=201)
@router.post('/api/comandos', status_code=201)
def post_command(body: CommandBody) -> dict[str, object]:
    try:
        actuator, action, value, is_message = CommandTranslator.normalize(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if is_message:
        text = str(value).strip()
        if not text:
            raise HTTPException(status_code=400, detail='El mensaje LCD no puede ir vacío.')
        return command_service.save_message(text)

    try:
        return command_service.publish_command(actuator, action, value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
