from __future__ import annotations

from datetime import datetime
from typing import Any

from app.core.topics import COMMAND_TOPIC_BY_ACTUATOR, TOPICS
from app.db.mongo import mongo
from app.services.mqtt_service import mqtt_service
from app.services.realtime import realtime_gateway
from app.services.state_store import state_store


class CommandService:
    @staticmethod
    def _critical(actuator: str, action: str) -> bool:
        return action in {'fire', 'stop-all', 'open', 'close', 'activate', 'deactivate', 'home'} or actuator == 'emergencia'

    def publish_command(self, actuator: str, action: str, value: Any = None, source: str = 'dashboard') -> dict[str, Any]:
        topic = COMMAND_TOPIC_BY_ACTUATOR.get(actuator)
        if topic is None:
            raise ValueError(f'No existe topic para el actuador: {actuator}')

        qos = 1 if self._critical(actuator, action) else 0
        timestamp = datetime.utcnow()
        payload = {
            'actuator': actuator,
            'action': action,
            'value': value,
            'source': source,
            'timestamp': timestamp.isoformat(),
        }
        mqtt_service.publish_json(topic, payload, qos=qos)

        document = {
            'actuator': actuator,
            'action': action,
            'value': value,
            'payload': payload,
            'source': source,
            'sourceTopic': topic,
            'qos': qos,
            'status': 'sent' if mqtt_service.connected else 'pending',
            'timestamp': timestamp,
        }
        command_id = None
        if mongo.is_connected:
            result = mongo.collection('commands').insert_one(document)
            command_id = str(result.inserted_id)

        patch = self._build_patch(actuator, action, value)
        if patch:
            state_store.update_actuator(patch['key'], patch['data'])
            realtime_gateway.emit_sync('actuator:update', {'type': patch['key'], 'data': patch['data']})
            realtime_gateway.emit_sync('telemetria_actualizada', patch['frontend'])

        if actuator == 'emergencia':
            state_store.update_system_state('emergencia')
            realtime_gateway.emit_sync('state:update', {'state': 'emergencia'})
            realtime_gateway.emit_sync('telemetria_actualizada', {'estadoNave': 'emergencia', 'timestamp': timestamp.isoformat()})

        response = {
            'id': command_id,
            'actuator': actuator,
            'action': action,
            'value': value,
            'qos': qos,
            'timestamp': timestamp.isoformat(),
            'status': document['status'],
            'topic': topic,
        }
        realtime_gateway.emit_sync('command:sent', response)
        return response

    def save_message(self, text: str, source: str = 'dashboard') -> dict[str, Any]:
        timestamp = datetime.utcnow()
        document = {
            'text': text,
            'source': source,
            'shownOnLcd': False,
            'timestamp': timestamp,
        }
        message_id = None
        if mongo.is_connected:
            result = mongo.collection('messages').insert_one(document)
            message_id = str(result.inserted_id)

        mqtt_service.publish_json(
            TOPICS['control']['messages'],
            {'text': text, 'source': source, 'timestamp': timestamp.isoformat()},
            qos=1,
        )

        payload = {
            'id': message_id,
            'text': text,
            'source': source,
            'timestamp': timestamp.isoformat(),
        }
        state_store.push_message(payload)
        realtime_gateway.emit_sync('message:new', payload)
        return payload

    @staticmethod
    def _build_patch(actuator: str, action: str, value: Any) -> dict[str, Any] | None:
        now = datetime.utcnow().isoformat()
        if actuator == 'torreta' and action == 'set-angle':
            angle = int(value or 0)
            return {
                'key': 'turret',
                'data': {'angle': angle, 'updatedAt': now},
                'frontend': {'anguloTorreta': angle, 'timestamp': now},
            }
        if actuator == 'torreta' and action == 'home':
            return {
                'key': 'turret',
                'data': {'angle': 0, 'updatedAt': now},
                'frontend': {'anguloTorreta': 0, 'timestamp': now},
            }
        if actuator == 'compuertas':
            status = 'Abierta' if action == 'open' else 'Cerrada'
            return {
                'key': 'doors',
                'data': {'status': status, 'updatedAt': now},
                'frontend': {'estadoCompuerta': status, 'timestamp': now},
            }
        if actuator == 'camuflaje':
            active = action == 'activate'
            return {
                'key': 'color',
                'data': {'sequence': [], 'camouflageActive': active, 'updatedAt': now},
                'frontend': {'modoCamuflaje': active, 'timestamp': now},
            }
        return None


command_service = CommandService()
