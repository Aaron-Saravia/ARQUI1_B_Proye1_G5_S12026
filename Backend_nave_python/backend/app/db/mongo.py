from __future__ import annotations

import logging
from typing import Any

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import Collection
from pymongo.database import Database

from app.core.config import settings

logger = logging.getLogger(__name__)


class MongoManager:
    def __init__(self) -> None:
        self.client: MongoClient[Any] | None = None
        self.db: Database[Any] | None = None

    def connect(self) -> None:
        self.client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        self.client.admin.command('ping')
        self.db = self.client[settings.mongodb_db]
        self._ensure_indexes()
        logger.info('Conectado a MongoDB en %s/%s', settings.mongodb_uri, settings.mongodb_db)

    def disconnect(self) -> None:
        if self.client is not None:
            self.client.close()
            logger.info('Conexión MongoDB cerrada')
        self.client = None
        self.db = None

    def _ensure_indexes(self) -> None:
        if self.db is None:
            return
        self.collection('sensor_readings').create_index([('sensorType', ASCENDING), ('timestamp', DESCENDING)])
        self.collection('events').create_index([('type', ASCENDING), ('timestamp', DESCENDING)])
        self.collection('commands').create_index([('actuator', ASCENDING), ('timestamp', DESCENDING)])
        self.collection('messages').create_index([('timestamp', DESCENDING)])

    @property
    def is_connected(self) -> bool:
        return self.db is not None

    def collection(self, name: str) -> Collection[Any]:
        if self.db is None:
            raise RuntimeError('MongoDB no está conectado')
        return self.db[name]


mongo = MongoManager()
