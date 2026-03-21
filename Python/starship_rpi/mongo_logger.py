"""MongoDB directo opcional.

Requiere: pip install pymongo python-dotenv
"""

from __future__ import annotations

from typing import Any

try:
    from pymongo import ASCENDING, MongoClient
except ImportError:  # pragma: no cover
    ASCENDING = None
    MongoClient = None

from .utils import utc_now_dt


class MongoLogger:
    def __init__(self, settings) -> None:
        self.enabled = bool(settings.enable_direct_mongo and MongoClient is not None)
        self.client = None
        self.db = None
        if not self.enabled:
            return
        try:
            self.client = MongoClient(settings.mongodb_uri, maxPoolSize=5)
            self.db = self.client[settings.mongodb_db]
            self._ensure_indexes()
            print('[Mongo] Conexion directa activa.')
        except Exception as exc:
            print(f'[Mongo] Desactivado por error: {exc}')
            self.enabled = False
            self.client = None
            self.db = None

    def _ensure_indexes(self) -> None:
        if not self.enabled or self.db is None:
            return
        for name in ('sensor_readings', 'events', 'commands', 'messages'):
            self.db[name].create_index([('timestamp', ASCENDING)])

    def log_sensor(self, sensor_name: str, payload: dict[str, Any]) -> None:
        if not self.enabled or self.db is None:
            return
        doc = {
            'sensor': sensor_name,
            'payload': payload,
            'timestamp': utc_now_dt(),
        }
        self.db['sensor_readings'].insert_one(doc)

    def log_event(self, category: str, event_type: str, severity: str, message: str, data: dict[str, Any] | None = None) -> None:
        if not self.enabled or self.db is None:
            return
        doc = {
            'category': category,
            'type': event_type,
            'severity': severity,
            'message': message,
            'data': data or {},
            'timestamp': utc_now_dt(),
        }
        self.db['events'].insert_one(doc)

    def log_command(self, source: str, target: str, action: str, payload: dict[str, Any] | None = None, status: str = 'ok') -> None:
        if not self.enabled or self.db is None:
            return
        doc = {
            'source': source,
            'target': target,
            'action': action,
            'payload': payload or {},
            'status': status,
            'timestamp': utc_now_dt(),
        }
        self.db['commands'].insert_one(doc)

    def log_message(self, text: str, source: str) -> None:
        if not self.enabled or self.db is None:
            return
        doc = {
            'text': text[:64],
            'source': source,
            'timestamp': utc_now_dt(),
        }
        self.db['messages'].insert_one(doc)

    def close(self) -> None:
        if self.client is not None:
            self.client.close()
