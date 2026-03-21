"""Orquestador principal del proyecto."""

from __future__ import annotations

import queue
import threading

import RPi.GPIO as GPIO

from .config import TOPICS, Settings
from .display import LcdService
from .hardware import (
    AlertBuzzer,
    ButtonsController,
    FansController,
    LaserLed,
    RgbCamouflage,
    ServoDoor,
    StatusLedPanel,
    StepperTurret,
)
from .mongo_logger import MongoLogger
from .mqtt_bridge import MqttBridge
from .sensors import DhtWorker, GasSensorDigital, ProximityWorker, TCS3200Worker, TCS34725Worker
from .state import SharedState
from .utils import utc_now_iso


class StarshipController:
    def __init__(self) -> None:
        self.settings = Settings()
        self.stop_event = threading.Event()
        self.state = SharedState(self.settings.device_id)
        self.mongo = MongoLogger(self.settings)
        self.command_queue: queue.Queue[tuple[str, str, dict]] = queue.Queue()
        self.telemetry_thread = threading.Thread(target=self._telemetry_worker, daemon=True)
        self.command_thread = threading.Thread(target=self._command_worker, daemon=True)
        self.sequence: list[str] = []
        self.last_color_seen = 'desconocido'
        self.last_published = {
            'gas': None,
            'proximity': None,
            'environment': None,
            'color': None,
            'state': None,
        }

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        self.mqtt = MqttBridge(self.settings, self._enqueue_mqtt_command)

        self.fans = FansController(self.settings) if self.settings.enable_fans else None
        self.laser = LaserLed(self.settings)
        self.buzzer = AlertBuzzer(self.settings) if self.settings.enable_buzzer else None
        self.rgb = RgbCamouflage(self.settings) if self.settings.enable_rgb else None
        self.doors = ServoDoor(self.settings) if self.settings.enable_doors else None
        self.turret = StepperTurret(self.settings) if self.settings.enable_turret else None
        self.status_leds = StatusLedPanel(self.settings) if self.settings.enable_status_leds else None
        self.lcd = LcdService(self.settings, self.state, self.stop_event)

        self.buttons = None
        if self.settings.enable_buttons:
            self.buttons = ButtonsController(self.settings, self._enqueue_button)

        self.gas_sensor = None
        if self.settings.enable_gas:
            self.gas_sensor = GasSensorDigital(self.settings, self._on_gas_change)

        self.dht_worker = None
        if self.settings.enable_dht:
            self.dht_worker = DhtWorker(self.settings, self.stop_event, self._on_environment)

        self.prox_worker = None
        if self.settings.enable_proximity:
            self.prox_worker = ProximityWorker(self.settings, self.stop_event, self._on_proximity)

        self.color_worker = None
        if self.settings.enable_color:
            if self.settings.color_sensor_is_tcs34725():
                self.color_worker = TCS34725Worker(self.settings, self.stop_event, self._on_color)
            else:
                self.color_worker = TCS3200Worker(self.settings, self.stop_event, self._on_color)

        if self.status_leds is not None:
            self.status_leds.set_snapshot_provider(self.state.snapshot)

    # ---------- ciclo de vida ----------

    def start(self) -> None:
        print('[APP] Iniciando core Python de la nave...')
        if self.buzzer is not None:
            self.buzzer.start()
        if self.rgb is not None:
            self.rgb.start()
        if self.status_leds is not None:
            self.status_leds.start()
        self.lcd.start()
        self.mqtt.start()
        self.command_thread.start()
        self.telemetry_thread.start()
        if self.dht_worker is not None:
            self.dht_worker.start()
        if self.prox_worker is not None:
            self.prox_worker.start()
        if self.color_worker is not None:
            self.color_worker.start()

        self._publish_boot_event()
        self._on_gas_change(self.gas_sensor.is_danger() if self.gas_sensor is not None else False)

    def wait_forever(self) -> None:
        self.stop_event.wait()

    def stop(self) -> None:
        if self.stop_event.is_set():
            return
        print('[APP] Cerrando...')
        self.stop_event.set()
        self.command_queue.put(('system', 'stop', {}))

        if self.dht_worker is not None:
            self.dht_worker.stop()
        if self.prox_worker is not None:
            self.prox_worker.stop()
        if self.color_worker is not None:
            self.color_worker.stop()
        if self.gas_sensor is not None:
            self.gas_sensor.cleanup()
        if self.buttons is not None:
            self.buttons.cleanup()
        if self.status_leds is not None:
            self.status_leds.stop()
        if self.rgb is not None:
            self.rgb.cleanup()
        if self.buzzer is not None:
            self.buzzer.stop()
        self.laser.cleanup()
        if self.doors is not None:
            self.doors.cleanup()
        if self.turret is not None:
            self.turret.cleanup()
        if self.fans is not None:
            self.fans.cleanup()
        self.lcd.stop()
        self.mqtt.stop()
        self.mongo.close()
        GPIO.cleanup()

    # ---------- workers ----------

    def _command_worker(self) -> None:
        while True:
            source, target, payload = self.command_queue.get()
            if source == 'system' and target == 'stop':
                break
            if source == 'button':
                self._handle_button(target)
            elif source == 'mqtt':
                self._handle_mqtt(target, payload)

    def _telemetry_worker(self) -> None:
        while not self.stop_event.is_set():
            snap = self.state.snapshot()
            self._maybe_publish_sensor('gas', TOPICS['sensors']['gas'], snap['gas'])
            self._maybe_publish_sensor('proximity', TOPICS['sensors']['proximity'], snap['proximity'])
            self._maybe_publish_sensor('environment', TOPICS['sensors']['environment'], snap['environment'])
            self._maybe_publish_sensor('color', TOPICS['sensors']['color'], {
                'color': snap['color']['color'],
                'sequence': snap['color']['sequence'],
                'camouflageActive': snap['color']['camouflageActive'],
                'data': snap['color']['data'],
                'timestamp': snap['color']['timestamp'],
            })
            self._maybe_publish_sensor('state', TOPICS['state']['general'], {
                'deviceId': snap['deviceId'],
                'status': snap['status'],
                'emergency': snap['emergency'],
                'turretAngle': snap['turret']['angle'],
                'doorsOpen': snap['doors']['open'],
                'camouflageActive': snap['color']['camouflageActive'],
                'shotsTotal': snap['stats']['shotsTotal'],
                'timestamp': snap['timestamp'],
            }, qos=1, retain=True)
            self.stop_event.wait(self.settings.telemetry_period_s)

    # ---------- entradas de sensores ----------

    def _on_environment(self, temperature: float, humidity: float) -> None:
        self.state.update_environment(temperature, humidity)
        if temperature > self.settings.temp_high_c or temperature < self.settings.temp_low_c:
            self._publish_alert(
                category='ambiente',
                alert_type='ALERT_TEMP',
                severity='warning',
                message=f'Temperatura fuera de rango: {temperature:.1f}C',
            )

    def _on_gas_change(self, danger: bool) -> None:
        old, new = self.state.update_gas(danger)
        if self.fans is not None:
            self.fans.set_on(new and not self.state.emergency)
        self._refresh_buzzer_mode()

        if new and not old:
            self.mongo.log_event('gas', 'gas_threshold', 'critical', 'Gas sobre umbral', self.state.snapshot()['gas'])
            self._publish_alert('gas', 'ALERT_GAS', 'critical', 'Gas sobre umbral seguro')
        elif old and not new:
            self.mongo.log_event('gas', 'gas_clear', 'info', 'Gas en nivel seguro', self.state.snapshot()['gas'])

    def _on_proximity(self, distance: float | None) -> None:
        level = self._classify_meteor_level(distance)
        old, new = self.state.update_proximity(distance, level)
        self._refresh_buzzer_mode()
        if new != old and new != 'none':
            self.mongo.log_event('meteorito', 'meteor_level', 'warning', f'Meteorito nivel {new}', self.state.snapshot()['proximity'])
            self._publish_alert('meteorito', 'ALERT_METEOR', 'warning', f'Meteorito nivel {new}')

    def _on_color(self, color_name: str, data: dict) -> None:
        if color_name != 'desconocido' and color_name != self.last_color_seen:
            self.last_color_seen = color_name
            self.sequence.append(color_name)
            self.sequence = self.sequence[-3:]
        self.state.update_color(color_name, data, self.sequence)
        if color_name != 'desconocido' and self.rgb is not None and not self.state.snapshot()['color']['camouflageActive']:
            self.rgb.show_named(color_name)

        if tuple(self.sequence) == self.settings.camouflage_sequence:
            if not self.state.snapshot()['color']['camouflageActive']:
                self._set_camouflage(True, source='sensor')

    # ---------- colas de comandos ----------

    def _enqueue_button(self, name: str) -> None:
        self.command_queue.put(('button', name, {}))

    def _enqueue_mqtt_command(self, topic: str, payload: dict) -> None:
        self.command_queue.put(('mqtt', topic, payload))

    # ---------- acciones ----------

    def _handle_button(self, name: str) -> None:
        if name == 'door_open':
            self._open_doors('button')
        elif name == 'door_close':
            self._close_doors('button')
        elif name == 'turret_left':
            self._move_turret_left('button', 12)
        elif name == 'turret_right':
            self._move_turret_right('button', 12)
        elif name == 'fire':
            self._fire_turret('button')
        elif name == 'emergency':
            self._set_emergency(not self.state.snapshot()['emergency'], 'button')

    def _handle_mqtt(self, topic: str, payload: dict) -> None:
        if topic == TOPICS['actuators']['doors']:
            action = payload.get('action', '').strip().lower()
            if action == 'open':
                self._open_doors('mqtt', payload)
            elif action == 'close':
                self._close_doors('mqtt', payload)
            elif action == 'toggle':
                if self.state.snapshot()['doors']['open']:
                    self._close_doors('mqtt', payload)
                else:
                    self._open_doors('mqtt', payload)

        elif topic == TOPICS['actuators']['turret']:
            action = payload.get('action', '').strip().lower()
            if action == 'set-angle':
                self._set_turret_angle(float(payload.get('value', 0)), 'mqtt', payload)
            elif action == 'left':
                self._move_turret_left('mqtt', float(payload.get('value', 10)))
            elif action == 'right':
                self._move_turret_right('mqtt', float(payload.get('value', 10)))
            elif action == 'home':
                self._set_turret_angle(0.0, 'mqtt', payload)
            elif action == 'retract':
                self._set_turret_angle(0.0, 'mqtt', payload)
            elif action == 'fire':
                self._fire_turret('mqtt', payload)

        elif topic == TOPICS['actuators']['fans']:
            action = payload.get('action', '').strip().lower()
            if action == 'on' and self.fans is not None:
                self.fans.set_on(True)
                self.mongo.log_command('mqtt', 'ventiladores', 'on', payload)
            elif action == 'off' and self.fans is not None:
                self.fans.set_on(False)
                self.mongo.log_command('mqtt', 'ventiladores', 'off', payload)
            elif action == 'auto':
                self._on_gas_change(self.state.snapshot()['gas']['danger'])
                self.mongo.log_command('mqtt', 'ventiladores', 'auto', payload)

        elif topic == TOPICS['actuators']['camouflage']:
            action = payload.get('action', '').strip().lower()
            if action == 'on':
                self._set_camouflage(True, source='mqtt')
            elif action == 'off':
                self._set_camouflage(False, source='mqtt')

        elif topic == TOPICS['control']['messages']:
            text = str(payload.get('text', '')).strip()[:64]
            if text:
                self.state.set_message(text, 'dashboard', self.settings.lcd_message_hold_s)
                self.mongo.log_message(text, 'dashboard')
                self.mongo.log_command('mqtt', 'lcd', 'message', payload)

        elif topic == TOPICS['control']['emergency']:
            action = payload.get('action', '').strip().lower()
            if action in {'on', 'true', '1'}:
                self._set_emergency(True, 'mqtt')
            elif action in {'off', 'reset', 'false', '0'}:
                self._set_emergency(False, 'mqtt')

    def _open_doors(self, source: str, payload: dict | None = None) -> None:
        if self.state.snapshot()['emergency'] or self.doors is None:
            return
        self.doors.open()
        self.state.set_doors_open(True)
        self.mongo.log_command(source, 'compuertas', 'open', payload)

    def _close_doors(self, source: str, payload: dict | None = None) -> None:
        if self.doors is None:
            return
        self.doors.close()
        self.state.set_doors_open(False)
        self.mongo.log_command(source, 'compuertas', 'close', payload)

    def _set_turret_angle(self, angle: float, source: str, payload: dict | None = None) -> None:
        if self.state.snapshot()['emergency'] or self.turret is None:
            return
        current = self.turret.set_angle(angle)
        self.state.set_turret_angle(current)
        self.mongo.log_command(source, 'torreta', 'set-angle', payload or {'value': angle})

    def _move_turret_left(self, source: str, degrees: float) -> None:
        if self.state.snapshot()['emergency'] or self.turret is None:
            return
        current = self.turret.nudge_left(degrees)
        self.state.set_turret_angle(current)
        self.mongo.log_command(source, 'torreta', 'left', {'value': degrees})

    def _move_turret_right(self, source: str, degrees: float) -> None:
        if self.state.snapshot()['emergency'] or self.turret is None:
            return
        current = self.turret.nudge_right(degrees)
        self.state.set_turret_angle(current)
        self.mongo.log_command(source, 'torreta', 'right', {'value': degrees})

    def _fire_turret(self, source: str, payload: dict | None = None) -> None:
        if self.state.snapshot()['emergency']:
            return
        self.laser.pulse(0.12)
        if self.buzzer is not None:
            previous = self._current_buzzer_mode()
            self.buzzer.set_mode('off')
            self.buzzer.pulse(0.08)
            self.buzzer.set_mode(previous)
        self.state.increment_shots()
        self.mongo.log_event('torreta', 'fire', 'info', 'Disparo ejecutado', {'timestamp': utc_now_iso()})
        self.mongo.log_command(source, 'torreta', 'fire', payload)

    def _set_camouflage(self, active: bool, source: str) -> None:
        self.state.set_camouflage(active)
        if self.rgb is not None:
            self.rgb.set_active(active)
        if active and self.turret is not None:
            current = self.turret.home()
            self.state.set_turret_angle(current)
        self.mongo.log_event('camuflaje', 'camouflage_toggle', 'info', f'Camuflaje {active}', self.state.snapshot()['color'])
        self.mongo.log_command(source, 'camuflaje', 'on' if active else 'off', {})

    def _set_emergency(self, active: bool, source: str) -> None:
        self.state.set_emergency(active)
        if active:
            if self.fans is not None:
                self.fans.set_on(False)
            if self.rgb is not None:
                self.rgb.set_active(False)
            if self.buzzer is not None:
                self.buzzer.set_mode('critical')
            self.mongo.log_event('emergency', 'emergency_on', 'critical', 'Modo emergencia activado', {})
            self._publish_alert('sistema', 'ALERT_EMERGENCY', 'critical', 'Modo emergencia activado')
        else:
            self._refresh_buzzer_mode()
            self.mongo.log_event('emergency', 'emergency_off', 'info', 'Modo emergencia desactivado', {})
            self._on_gas_change(self.state.snapshot()['gas']['danger'])
        self.mongo.log_command(source, 'emergency', 'on' if active else 'off', {})

    # ---------- utilidades ----------

    def _classify_meteor_level(self, distance: float | None) -> str:
        if distance is None or distance > self.settings.meteor_max_cm:
            return 'none'
        if distance < self.settings.meteor_critical_cm:
            return 'critical'
        if distance <= self.settings.meteor_far_cm:
            return 'near'
        return 'far'

    def _current_buzzer_mode(self) -> str:
        snap = self.state.snapshot()
        if snap['emergency']:
            return 'critical'
        if snap['alerts']['fire']:
            return 'fire'
        level = snap['proximity']['level']
        if level in {'far', 'near', 'critical'}:
            return level
        return 'off'

    def _refresh_buzzer_mode(self) -> None:
        if self.buzzer is None:
            return
        self.buzzer.set_mode(self._current_buzzer_mode())

    def _maybe_publish_sensor(self, key: str, topic: str, payload: dict, qos: int = 0, retain: bool = False) -> None:
        timestamp = payload.get('timestamp')
        if not timestamp:
            return
        if self.last_published[key] == timestamp:
            return
        self.last_published[key] = timestamp
        wrapped = {'deviceId': self.settings.device_id, **payload}
        self.mqtt.publish_json(topic, wrapped, qos=qos, retain=retain)
        if key in {'gas', 'proximity', 'environment', 'color'}:
            self.mongo.log_sensor(key, wrapped)

    def _publish_alert(self, category: str, alert_type: str, severity: str, message: str) -> None:
        payload = {
            'deviceId': self.settings.device_id,
            'type': alert_type,
            'category': category,
            'severity': severity,
            'message': message,
            'timestamp': utc_now_iso(),
        }
        self.mqtt.publish_json(TOPICS['alerts']['critical'], payload, qos=1, retain=False)

    def _publish_boot_event(self) -> None:
        self.mongo.log_event('sistema', 'boot', 'info', 'Core Python iniciado', {})
        self.mqtt.publish_json(
            TOPICS['state']['general'],
            {
                'deviceId': self.settings.device_id,
                'status': 'operativa',
                'boot': True,
                'timestamp': utc_now_iso(),
            },
            qos=1,
            retain=True,
        )
