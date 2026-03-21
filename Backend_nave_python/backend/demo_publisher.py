from __future__ import annotations

import json
import math
import random
import time
from datetime import datetime
from urllib.parse import urlparse

import paho.mqtt.client as mqtt

MQTT_URL = 'mqtt://127.0.0.1:1883'
TOPICS = {
    'gas': 'nave/sensores/gas',
    'proximity': 'nave/sensores/proximidad',
    'environment': 'nave/sensores/ambiente',
    'color': 'nave/sensores/color',
}
COLORS = [
    ['rojo', 'amarillo', 'azul'],
    ['verde', 'azul', 'violeta'],
    ['gris', 'negro', 'azul'],
]


def client_from_url(url: str) -> mqtt.Client:
    parsed = urlparse(url)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or 1883
    client = mqtt.Client()
    client.connect(host, port, 60)
    client.loop_start()
    return client


def publish(client: mqtt.Client, topic: str, payload: dict) -> None:
    client.publish(topic, json.dumps(payload), qos=0)


if __name__ == '__main__':
    client = client_from_url(MQTT_URL)
    started = time.time()
    try:
        while True:
            elapsed = time.time() - started
            gas = 40 + int((math.sin(elapsed / 8) + 1) * 30) + random.randint(0, 10)
            proximity = max(5, 120 - int((math.sin(elapsed / 5) + 1) * 45) - random.randint(0, 10))
            sequence = random.choice(COLORS)
            now = datetime.utcnow().isoformat()

            publish(client, TOPICS['gas'], {
                'value': gas,
                'unit': 'ppm',
                'threshold': 80,
                'danger': gas > 80,
                'timestamp': now,
            })
            publish(client, TOPICS['proximity'], {
                'value': proximity,
                'unit': 'cm',
                'level': 'critical' if proximity < 20 else 'near' if proximity <= 50 else 'far',
                'timestamp': now,
            })
            publish(client, TOPICS['environment'], {
                'temperature': round(20 + random.random() * 12, 1),
                'humidity': round(35 + random.random() * 40, 1),
                'timestamp': now,
            })
            publish(client, TOPICS['color'], {
                'sequence': sequence,
                'camouflageActive': random.choice([True, False]),
                'timestamp': now,
            })
            time.sleep(5)
    except KeyboardInterrupt:
        client.loop_stop()
        client.disconnect()
