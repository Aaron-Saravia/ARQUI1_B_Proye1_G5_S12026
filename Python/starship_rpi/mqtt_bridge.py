"""Capa MQTT.

Requiere: pip install paho-mqtt
Nota: paho-mqtt 2.x cambio callbacks; se fija VERSION1 para mantener esta firma.
"""

from __future__ import annotations

import json
from typing import Any, Callable

from paho.mqtt import client as mqtt_client

from .config import SUBSCRIPTIONS


class MqttBridge:
    def __init__(self, settings, on_command: Callable[[str, dict[str, Any]], None]) -> None:
        self.settings = settings
        self.on_command = on_command
        self.client = mqtt_client.Client(
            callback_api_version=mqtt_client.CallbackAPIVersion.VERSION1,
            client_id=settings.device_id,
            protocol=mqtt_client.MQTTv311,
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.reconnect_delay_set(min_delay=1, max_delay=20)
        if settings.mqtt_username:
            self.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print('[MQTT] Conectado.')
            for topic in SUBSCRIPTIONS:
                client.subscribe(topic, qos=1)
                print(f'[MQTT] Subscrito a {topic}')
        else:
            print(f'[MQTT] Error de conexion: {rc}')

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print('[MQTT] Desconexion inesperada. Reintentando...')

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode('utf-8')) if msg.payload else {}
        except json.JSONDecodeError:
            print(f'[MQTT] JSON invalido en {msg.topic}')
            return
        self.on_command(msg.topic, payload)

    def start(self) -> None:
        self.client.connect(self.settings.mqtt_host, self.settings.mqtt_port, keepalive=self.settings.mqtt_keepalive)
        self.client.loop_start()

    def publish_json(self, topic: str, payload: dict[str, Any], qos: int = 0, retain: bool = False) -> None:
        self.client.publish(topic, json.dumps(payload), qos=qos, retain=retain)

    def stop(self) -> None:
        try:
            self.client.disconnect()
        finally:
            self.client.loop_stop()
