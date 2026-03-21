from __future__ import annotations

import json
import logging
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Any

from bson import ObjectId

from app.core.config import settings
from app.core.topics import TOPICS
from app.db.mongo import mongo
from app.services.realtime import realtime_gateway
from app.services.state_store import state_store

logger = logging.getLogger(__name__)


class TelemetryProcessor:
    @staticmethod
    def safe_parse(raw_message: str) -> dict[str, Any]:
        try:
            return json.loads(raw_message)
        except json.JSONDecodeError:
            return {'raw': raw_message}

    @staticmethod
    def normalize_timestamp(value: Any) -> datetime:
        if isinstance(value, datetime):
            return value
        if isinstance(value, str) and value:
            try:
                return datetime.fromisoformat(value.replace('Z', '+00:00')).replace(tzinfo=None)
            except ValueError:
                return datetime.utcnow()
        return datetime.utcnow()

    @staticmethod
    def level_from_distance(distance: float) -> str:
        if distance < 20:
            return 'critical'
        if distance <= 50:
            return 'near'
        return 'far'

    def _insert_one(self, collection_name: str, payload: dict[str, Any]) -> str | None:
        if not mongo.is_connected:
            return None
        result = mongo.collection(collection_name).insert_one(payload)
        return str(result.inserted_id)

    def save_sensor_reading(
        self,
        sensor_type: str,
        value: Any,
        unit: str,
        source_topic: str,
        raw_payload: dict[str, Any],
        timestamp: datetime,
    ) -> str | None:
        return self._insert_one(
            'sensor_readings',
            {
                'sensorType': sensor_type,
                'value': value,
                'unit': unit,
                'sourceTopic': source_topic,
                'rawPayload': raw_payload,
                'timestamp': timestamp,
            },
        )

    def save_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        source_topic: str,
        payload: dict[str, Any],
        timestamp: datetime,
    ) -> str | None:
        return self._insert_one(
            'events',
            {
                'type': event_type,
                'severity': severity,
                'message': message,
                'sourceTopic': source_topic,
                'payload': payload,
                'timestamp': timestamp,
            },
        )

    def process_message(self, topic: str, raw_message: str) -> None:
        payload = self.safe_parse(raw_message)
        try:
            if topic == TOPICS['sensors']['gas']:
                self.handle_gas(topic, payload)
            elif topic == TOPICS['sensors']['proximity']:
                self.handle_proximity(topic, payload)
            elif topic == TOPICS['sensors']['environment']:
                self.handle_environment(topic, payload)
            elif topic == TOPICS['sensors']['color']:
                self.handle_color(topic, payload)
            elif topic == TOPICS['alerts']['critical']:
                self.handle_critical_alert(topic, payload)
            elif topic == TOPICS['state']['general']:
                self.handle_state(payload)
            else:
                logger.info('Topic no manejado aún: %s', topic)
        except Exception as exc:  # pragma: no cover - seguridad operacional
            logger.exception('Error procesando topic %s: %s', topic, exc)

    def handle_gas(self, topic: str, payload: dict[str, Any]) -> None:
        ts = self.normalize_timestamp(payload.get('timestamp'))
        data = {
            'value': float(payload.get('value', payload.get('level', 0)) or 0),
            'unit': payload.get('unit', 'ppm'),
            'threshold': float(payload.get('threshold', 250) or 250),
            'danger': bool(payload.get('danger', False)),
            'updatedAt': ts.isoformat(),
        }
        self.save_sensor_reading('gas', data['value'], data['unit'], topic, payload, ts)
        state_store.update_sensor('gas', data)
        realtime_gateway.emit_sync('sensor:update', {'type': 'gas', 'data': data})
        realtime_gateway.emit_sync('telemetria_actualizada', {'gas': data['value'], 'timestamp': ts.isoformat()})

    def handle_proximity(self, topic: str, payload: dict[str, Any]) -> None:
        ts = self.normalize_timestamp(payload.get('timestamp'))
        value = float(payload.get('value', payload.get('distance', 0)) or 0)
        data = {
            'value': value,
            'unit': payload.get('unit', 'cm'),
            'level': payload.get('level', self.level_from_distance(value)),
            'updatedAt': ts.isoformat(),
        }
        self.save_sensor_reading('proximity', value, data['unit'], topic, payload, ts)
        state_store.update_sensor('proximity', data)
        realtime_gateway.emit_sync('sensor:update', {'type': 'proximity', 'data': data})
        realtime_gateway.emit_sync('telemetria_actualizada', {'distanciaMeteorito': value, 'timestamp': ts.isoformat()})

    def handle_environment(self, topic: str, payload: dict[str, Any]) -> None:
        ts = self.normalize_timestamp(payload.get('timestamp'))
        data = {
            'temperature': float(payload.get('temperature', 0) or 0),
            'humidity': float(payload.get('humidity', 0) or 0),
            'updatedAt': ts.isoformat(),
        }
        self.save_sensor_reading('temperature', data['temperature'], 'C', topic, payload, ts)
        self.save_sensor_reading('humidity', data['humidity'], '%', topic, payload, ts)
        state_store.update_sensor('environment', data)
        realtime_gateway.emit_sync('sensor:update', {'type': 'environment', 'data': data})
        realtime_gateway.emit_sync(
            'telemetria_actualizada',
            {'temperatura': data['temperature'], 'humedad': data['humidity'], 'timestamp': ts.isoformat()},
        )

    def handle_color(self, topic: str, payload: dict[str, Any]) -> None:
        ts = self.normalize_timestamp(payload.get('timestamp'))
        sequence = payload.get('sequence') if isinstance(payload.get('sequence'), list) else []
        data = {
            'sequence': sequence,
            'camouflageActive': bool(payload.get('camouflageActive', False)),
            'updatedAt': ts.isoformat(),
        }
        self.save_sensor_reading('color', ','.join(sequence), '', topic, payload, ts)
        state_store.update_sensor('color', data)
        color_text = ' / '.join(sequence) if sequence else 'Ninguno'
        realtime_gateway.emit_sync('sensor:update', {'type': 'color', 'data': data})
        realtime_gateway.emit_sync(
            'telemetria_actualizada',
            {'colorCamuflaje': color_text, 'modoCamuflaje': data['camouflageActive'], 'timestamp': ts.isoformat()},
        )

    def handle_critical_alert(self, topic: str, payload: dict[str, Any]) -> None:
        ts = self.normalize_timestamp(payload.get('timestamp'))
        event_type = payload.get('type', 'CRITICAL_ALERT')
        severity = payload.get('severity', 'critical')
        message = payload.get('message', 'Alerta crítica recibida')
        inserted_id = self.save_event(event_type, severity, message, topic, payload, ts)
        data = {
            'id': inserted_id,
            'type': event_type,
            'severity': severity,
            'message': message,
            'timestamp': ts.isoformat(),
            'payload': payload,
        }
        state_store.push_event(data)
        state_store.update_system_state('emergencia' if severity == 'critical' else 'alerta')
        realtime_gateway.emit_sync('event:new', data)
        realtime_gateway.emit_sync('state:update', {'state': 'emergencia' if severity == 'critical' else 'alerta'})

    def handle_state(self, payload: dict[str, Any]) -> None:
        state = str(payload.get('state', payload.get('status', 'operativa')))
        state_store.update_system_state(state)
        realtime_gateway.emit_sync('state:update', {'state': state})
        realtime_gateway.emit_sync('telemetria_actualizada', {'estadoNave': state, 'timestamp': datetime.utcnow().isoformat()})

    def latest_sensor_history(self, sensor_type: str, hours: int = 24, limit: int = 300) -> list[dict[str, Any]]:
        if not mongo.is_connected:
            return []
        from_date = datetime.utcnow() - timedelta(hours=hours)
        cursor = (
            mongo.collection('sensor_readings')
            .find({'sensorType': sensor_type, 'timestamp': {'$gte': from_date}})
            .sort('timestamp', 1)
            .limit(limit)
        )
        return [self.serialize_document(doc) for doc in cursor]

    def chart_history(self, hours: int | None = None, bucket_minutes: int | None = None) -> list[dict[str, Any]]:
        if not mongo.is_connected:
            return []
        hours = hours or settings.history_default_hours
        bucket_minutes = bucket_minutes or settings.chart_bucket_minutes
        from_date = datetime.utcnow() - timedelta(hours=hours)
        cursor = (
            mongo.collection('sensor_readings')
            .find({'sensorType': {'$in': ['gas', 'proximity', 'temperature', 'humidity']}, 'timestamp': {'$gte': from_date}})
            .sort('timestamp', 1)
        )
        buckets: OrderedDict[str, dict[str, Any]] = OrderedDict()
        last_values = {'gas': None, 'meteorito': None, 'temperatura': None, 'humedad': None}

        for raw_doc in cursor:
            doc = self.serialize_document(raw_doc)
            ts = doc['timestamp']
            if isinstance(ts, str):
                dt = self.normalize_timestamp(ts)
            else:
                dt = ts
            bucket_dt = dt.replace(second=0, microsecond=0)
            minute_mod = bucket_dt.minute % bucket_minutes
            bucket_dt = bucket_dt - timedelta(minutes=minute_mod)
            key = bucket_dt.isoformat()
            if key not in buckets:
                buckets[key] = {
                    'timestamp': bucket_dt.isoformat(),
                    'hora': bucket_dt.strftime('%H:%M'),
                    'gas': last_values['gas'],
                    'meteorito': last_values['meteorito'],
                    'temperatura': last_values['temperatura'],
                    'humedad': last_values['humedad'],
                }

            if doc['sensorType'] == 'gas':
                buckets[key]['gas'] = doc['value']
                last_values['gas'] = doc['value']
            elif doc['sensorType'] == 'proximity':
                buckets[key]['meteorito'] = doc['value']
                last_values['meteorito'] = doc['value']
            elif doc['sensorType'] == 'temperature':
                buckets[key]['temperatura'] = doc['value']
                last_values['temperatura'] = doc['value']
            elif doc['sensorType'] == 'humidity':
                buckets[key]['humedad'] = doc['value']
                last_values['humedad'] = doc['value']

        return list(buckets.values())

    @staticmethod
    def serialize_document(doc: dict[str, Any]) -> dict[str, Any]:
        output = dict(doc)
        if isinstance(output.get('_id'), ObjectId):
            output['id'] = str(output.pop('_id'))
        timestamp = output.get('timestamp')
        if isinstance(timestamp, datetime):
            output['timestamp'] = timestamp.isoformat()
        return output


telemetry_processor = TelemetryProcessor()
