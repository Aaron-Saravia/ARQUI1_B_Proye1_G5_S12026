from __future__ import annotations

import json
import logging
from typing import Any, Callable

import paho.mqtt.client as mqtt

from app.core.config import settings

logger = logging.getLogger(__name__)


class MQTTService:
    def __init__(self) -> None:
        self.client: mqtt.Client | None = None
        self.connected = False
        self._on_message_handler: Callable[[str, str], None] | None = None
        self._subscriptions: list[str] = []

    def connect(self, subscriptions: list[str], on_message: Callable[[str, str], None]) -> None:
        self._subscriptions = subscriptions
        self._on_message_handler = on_message

        try:
            self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=settings.mqtt_client_id, transport=settings.mqtt_transport)
        except AttributeError:
            self.client = mqtt.Client(client_id=settings.mqtt_client_id, transport=settings.mqtt_transport)

        if settings.mqtt_user:
            self.client.username_pw_set(settings.mqtt_user, settings.mqtt_password)

        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_log = self._on_log

        self.client.connect(settings.mqtt_host, settings.mqtt_port, keepalive=60)
        self.client.loop_start()
        logger.info('Conexión MQTT inicializada hacia %s:%s', settings.mqtt_host, settings.mqtt_port)

    def disconnect(self) -> None:
        if self.client is None:
            return
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
        logger.info('Cliente MQTT desconectado')

    def publish_json(self, topic: str, payload: dict[str, Any], qos: int = 0, retain: bool = False) -> bool:
        if self.client is None or not self.connected:
            logger.warning('No se publicó en MQTT porque no hay conexión activa: %s', topic)
            return False
        result = self.client.publish(topic, json.dumps(payload), qos=qos, retain=retain)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def _on_connect(self, client: mqtt.Client, _userdata: Any, _flags: Any, rc: int, *_args: Any) -> None:
        self.connected = rc == 0
        if rc != 0:
            logger.error('No se pudo conectar a MQTT. rc=%s', rc)
            return
        logger.info('Conectado al broker MQTT')
        for topic in self._subscriptions:
            client.subscribe(topic, qos=0)
        logger.info('Suscripciones MQTT listas: %s', ', '.join(self._subscriptions))

    def _on_disconnect(self, _client: mqtt.Client, _userdata: Any, rc: int, *_args: Any) -> None:
        self.connected = False
        if rc != 0:
            logger.warning('MQTT se desconectó inesperadamente. rc=%s', rc)
        else:
            logger.info('MQTT desconectado')

    def _on_message(self, _client: mqtt.Client, _userdata: Any, msg: mqtt.MQTTMessage) -> None:
        if self._on_message_handler is None:
            return
        payload = msg.payload.decode('utf-8', errors='ignore')
        self._on_message_handler(msg.topic, payload)

    def _on_log(self, _client: mqtt.Client, _userdata: Any, level: int, buf: str) -> None:
        if level == mqtt.MQTT_LOG_ERR:
            logger.error('MQTT: %s', buf)


mqtt_service = MQTTService()
