"""Estado compartido del sistema."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any

from .utils import utc_now_iso


@dataclass
class SharedState:
    device_id: str
    lock: threading.RLock = field(default_factory=threading.RLock, init=False)

    gas: dict[str, Any] = field(default_factory=lambda: {
        'value': 0,
        'unit': 'digital',
        'threshold': 1,
        'danger': False,
        'timestamp': None,
    })
    environment: dict[str, Any] = field(default_factory=lambda: {
        'temperature': None,
        'humidity': None,
        'timestamp': None,
    })
    proximity: dict[str, Any] = field(default_factory=lambda: {
        'value': None,
        'unit': 'cm',
        'level': 'none',
        'timestamp': None,
    })
    color: dict[str, Any] = field(default_factory=lambda: {
        'color': 'desconocido',
        'sequence': [],
        'camouflageActive': False,
        'data': {},
        'timestamp': None,
    })
    turret: dict[str, Any] = field(default_factory=lambda: {
        'angle': 0.0,
        'timestamp': None,
    })
    doors: dict[str, Any] = field(default_factory=lambda: {
        'open': False,
        'timestamp': None,
    })
    message: dict[str, Any] = field(default_factory=lambda: {
        'text': '',
        'source': '',
        'timestamp': None,
        'expiresAt': 0.0,
    })
    alerts: dict[str, Any] = field(default_factory=lambda: {
        'fire': False,
        'meteor': False,
        'camouflage': False,
    })
    stats: dict[str, Any] = field(default_factory=lambda: {
        'shotsTotal': 0,
        'camouflageSeconds': 0.0,
        'gasAlerts': 0,
        'meteorAlerts': 0,
    })
    emergency: bool = False
    status: str = 'operativa'
    updated_at: str | None = None
    _camouflage_started_monotonic: float | None = None

    def _touch(self) -> None:
        self.updated_at = utc_now_iso()
        self._recompute_status_locked()

    def _recompute_status_locked(self) -> None:
        if self.emergency:
            self.status = 'emergencia'
        elif self.alerts['fire'] or self.alerts['meteor']:
            self.status = 'alerta'
        else:
            self.status = 'operativa'

    def update_environment(self, temperature: float, humidity: float) -> None:
        with self.lock:
            self.environment.update({
                'temperature': round(temperature, 1),
                'humidity': round(humidity, 1),
                'timestamp': utc_now_iso(),
            })
            self._touch()

    def update_gas(self, danger: bool) -> tuple[bool, bool]:
        with self.lock:
            old = bool(self.gas['danger'])
            self.gas.update({
                'value': 1 if danger else 0,
                'danger': danger,
                'timestamp': utc_now_iso(),
            })
            self.alerts['fire'] = danger
            if danger and not old:
                self.stats['gasAlerts'] += 1
            self._touch()
            return old, danger

    def update_proximity(self, distance: float | None, level: str) -> tuple[str, str]:
        with self.lock:
            old = str(self.proximity['level'])
            self.proximity.update({
                'value': round(distance, 1) if distance is not None else None,
                'level': level,
                'timestamp': utc_now_iso(),
            })
            self.alerts['meteor'] = level != 'none'
            if level != 'none' and level != old:
                self.stats['meteorAlerts'] += 1
            self._touch()
            return old, level

    def update_color(self, color_name: str, data: dict[str, Any], sequence: list[str]) -> None:
        with self.lock:
            self.color.update({
                'color': color_name,
                'sequence': sequence[:],
                'data': data,
                'timestamp': utc_now_iso(),
            })
            self._touch()

    def set_camouflage(self, active: bool) -> None:
        with self.lock:
            already = bool(self.color['camouflageActive'])
            self.color['camouflageActive'] = active
            self.alerts['camouflage'] = active
            if active and not already:
                self._camouflage_started_monotonic = time.monotonic()
            elif not active and already and self._camouflage_started_monotonic is not None:
                self.stats['camouflageSeconds'] += time.monotonic() - self._camouflage_started_monotonic
                self._camouflage_started_monotonic = None
            self._touch()

    def set_turret_angle(self, angle: float) -> None:
        with self.lock:
            self.turret.update({'angle': round(angle, 1), 'timestamp': utc_now_iso()})
            self._touch()

    def set_doors_open(self, is_open: bool) -> None:
        with self.lock:
            self.doors.update({'open': is_open, 'timestamp': utc_now_iso()})
            self._touch()

    def set_message(self, text: str, source: str, hold_seconds: float = 5.0) -> None:
        with self.lock:
            self.message.update({
                'text': text[:64],
                'source': source,
                'timestamp': utc_now_iso(),
                'expiresAt': time.monotonic() + hold_seconds,
            })
            self._touch()

    def current_message(self) -> str:
        with self.lock:
            if self.message['text'] and time.monotonic() < float(self.message['expiresAt']):
                return str(self.message['text'])
            return ''

    def increment_shots(self) -> None:
        with self.lock:
            self.stats['shotsTotal'] += 1
            self._touch()

    def set_emergency(self, active: bool) -> None:
        with self.lock:
            self.emergency = active
            self._touch()

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            camouflage_seconds = float(self.stats['camouflageSeconds'])
            if self.color['camouflageActive'] and self._camouflage_started_monotonic is not None:
                camouflage_seconds += time.monotonic() - self._camouflage_started_monotonic
            return {
                'deviceId': self.device_id,
                'gas': dict(self.gas),
                'environment': dict(self.environment),
                'proximity': dict(self.proximity),
                'color': dict(self.color),
                'turret': dict(self.turret),
                'doors': dict(self.doors),
                'message': dict(self.message),
                'alerts': dict(self.alerts),
                'stats': {
                    'shotsTotal': int(self.stats['shotsTotal']),
                    'camouflageSeconds': round(camouflage_seconds, 1),
                    'gasAlerts': int(self.stats['gasAlerts']),
                    'meteorAlerts': int(self.stats['meteorAlerts']),
                },
                'emergency': bool(self.emergency),
                'status': self.status,
                'timestamp': self.updated_at or utc_now_iso(),
            }
