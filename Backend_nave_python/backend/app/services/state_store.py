from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Any


@dataclass
class StateStore:
    lock: Lock = field(default_factory=Lock)
    system_state: str = 'operativa'
    sensors: dict[str, Any] = field(
        default_factory=lambda: {
            'gas': {'value': 0, 'unit': 'ppm', 'threshold': 250, 'danger': False, 'updatedAt': None},
            'proximity': {'value': 0, 'unit': 'cm', 'level': 'far', 'updatedAt': None},
            'environment': {'temperature': 0, 'humidity': 0, 'updatedAt': None},
            'color': {'sequence': [], 'camouflageActive': False, 'updatedAt': None},
            'turret': {'angle': 0, 'updatedAt': None},
            'doors': {'status': 'Cerrada', 'updatedAt': None},
        }
    )
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    recent_messages: list[dict[str, Any]] = field(default_factory=list)

    def update_system_state(self, next_state: str) -> None:
        with self.lock:
            self.system_state = next_state

    def update_sensor(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.sensors[key] = payload

    def update_actuator(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.sensors[key] = payload

    def push_event(self, payload: dict[str, Any]) -> None:
        with self.lock:
            self.recent_events.insert(0, payload)
            self.recent_events = self.recent_events[:20]

    def push_message(self, payload: dict[str, Any]) -> None:
        with self.lock:
            self.recent_messages.insert(0, payload)
            self.recent_messages = self.recent_messages[:10]

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                'systemState': self.system_state,
                'sensors': deepcopy(self.sensors),
                'recentEvents': deepcopy(self.recent_events),
                'recentMessages': deepcopy(self.recent_messages),
            }

    def frontend_payload(self) -> dict[str, Any]:
        snap = self.snapshot()
        color_sequence = snap['sensors']['color'].get('sequence') or []
        color_text = ' / '.join(color_sequence) if color_sequence else 'Ninguno'
        return {
            'gas': snap['sensors']['gas'].get('value', 0),
            'distanciaMeteorito': snap['sensors']['proximity'].get('value', 0),
            'colorCamuflaje': color_text,
            'estadoCompuerta': snap['sensors']['doors'].get('status', 'Cerrada'),
            'temperatura': snap['sensors']['environment'].get('temperature', 0),
            'humedad': snap['sensors']['environment'].get('humidity', 0),
            'anguloTorreta': snap['sensors']['turret'].get('angle', 0),
            'modoCamuflaje': snap['sensors']['color'].get('camouflageActive', False),
            'estadoNave': snap['systemState'],
            'timestamp': datetime.utcnow().isoformat(),
        }


state_store = StateStore()
