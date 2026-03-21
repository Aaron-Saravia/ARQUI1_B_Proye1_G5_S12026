"""Actuadores y entradas fisicas."""

from __future__ import annotations

import queue
import threading
import time
from typing import Callable

import RPi.GPIO as GPIO

from .utils import clamp


class FansController:
    def __init__(self, settings) -> None:
        self.pins = tuple(settings.fan_pins)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        self.is_on = False

    def set_on(self, enabled: bool) -> None:
        self.is_on = enabled
        for pin in self.pins:
            GPIO.output(pin, GPIO.HIGH if enabled else GPIO.LOW)

    def cleanup(self) -> None:
        self.set_on(False)


class LaserLed:
    def __init__(self, settings) -> None:
        self.pin = settings.shot_led_pin
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

    def pulse(self, duration_s: float = 0.15) -> None:
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(duration_s)
        GPIO.output(self.pin, GPIO.LOW)

    def cleanup(self) -> None:
        GPIO.output(self.pin, GPIO.LOW)


class ServoDoor:
    def __init__(self, settings) -> None:
        self.pin = settings.servo_pin
        self.open_angle = settings.servo_open_angle
        self.closed_angle = settings.servo_closed_angle
        GPIO.setup(self.pin, GPIO.OUT)
        self.pwm = GPIO.PWM(self.pin, 50)
        self.pwm.start(0)
        self.is_open = False
        self.close()

    def _duty_for_angle(self, angle: float) -> float:
        angle = clamp(angle, 0, 180)
        return 2.5 + (angle / 18.0)

    def _move_to(self, angle: float) -> None:
        self.pwm.ChangeDutyCycle(self._duty_for_angle(angle))
        time.sleep(0.35)
        self.pwm.ChangeDutyCycle(0)

    def open(self) -> None:
        self._move_to(self.open_angle)
        self.is_open = True

    def close(self) -> None:
        self._move_to(self.closed_angle)
        self.is_open = False

    def toggle(self) -> None:
        if self.is_open:
            self.close()
        else:
            self.open()

    def cleanup(self) -> None:
        self.pwm.ChangeDutyCycle(0)
        self.pwm.stop()


class StepperTurret:
    HALF_STEP = [
        (1, 0, 0, 0),
        (1, 1, 0, 0),
        (0, 1, 0, 0),
        (0, 1, 1, 0),
        (0, 0, 1, 0),
        (0, 0, 1, 1),
        (0, 0, 0, 1),
        (1, 0, 0, 1),
    ]

    def __init__(self, settings) -> None:
        self.pins = tuple(settings.stepper_pins)
        self.step_delay_s = settings.stepper_step_delay_s
        self.steps_per_rev = settings.stepper_steps_per_rev
        self.current_angle = 0.0
        self.lock = threading.RLock()
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    def _release(self) -> None:
        for pin in self.pins:
            GPIO.output(pin, GPIO.LOW)

    def _run_steps(self, steps: int) -> None:
        if steps == 0:
            return
        seq = self.HALF_STEP if steps > 0 else list(reversed(self.HALF_STEP))
        for _ in range(abs(steps)):
            for pattern in seq:
                for pin, state in zip(self.pins, pattern):
                    GPIO.output(pin, state)
                time.sleep(self.step_delay_s)
        self._release()

    def set_angle(self, target_angle: float) -> float:
        target_angle = float(target_angle) % 360.0
        with self.lock:
            delta = target_angle - self.current_angle
            if delta > 180:
                delta -= 360
            elif delta < -180:
                delta += 360
            steps = int((delta / 360.0) * self.steps_per_rev)
            self._run_steps(steps)
            self.current_angle = target_angle
            return self.current_angle

    def nudge_left(self, degrees: float = 10.0) -> float:
        return self.set_angle(self.current_angle - abs(degrees))

    def nudge_right(self, degrees: float = 10.0) -> float:
        return self.set_angle(self.current_angle + abs(degrees))

    def home(self) -> float:
        return self.set_angle(0.0)

    def cleanup(self) -> None:
        self._release()


class AlertBuzzer:
    def __init__(self, settings) -> None:
        self.pin = settings.buzzer_pin
        self.mode = 'off'
        self.lock = threading.RLock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        GPIO.setup(self.pin, GPIO.OUT, initial=GPIO.LOW)

    def start(self) -> None:
        self.thread.start()

    def set_mode(self, mode: str) -> None:
        with self.lock:
            self.mode = mode

    def _beep(self, on_s: float, off_s: float) -> None:
        GPIO.output(self.pin, GPIO.HIGH)
        if self.stop_event.wait(on_s):
            return
        GPIO.output(self.pin, GPIO.LOW)
        self.stop_event.wait(off_s)

    def _worker(self) -> None:
        while not self.stop_event.is_set():
            with self.lock:
                mode = self.mode
            if mode == 'critical':
                GPIO.output(self.pin, GPIO.HIGH)
                self.stop_event.wait(0.1)
            elif mode == 'near':
                self._beep(0.08, 0.08)
                self._beep(0.08, 0.08)
                self._beep(0.08, 0.58)
            elif mode == 'far':
                self._beep(0.10, 1.90)
            elif mode == 'fire':
                self._beep(0.15, 0.15)
            else:
                GPIO.output(self.pin, GPIO.LOW)
                self.stop_event.wait(0.1)
        GPIO.output(self.pin, GPIO.LOW)

    def pulse(self, duration_s: float = 0.12) -> None:
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(duration_s)
        GPIO.output(self.pin, GPIO.LOW)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        GPIO.output(self.pin, GPIO.LOW)


class RgbCamouflage:
    COLOR_MAP = {
        'rojo': (100, 0, 0),
        'amarillo': (100, 65, 0),
        'azul': (0, 0, 100),
        'verde': (0, 100, 0),
        'apagado': (0, 0, 0),
    }

    def __init__(self, settings) -> None:
        self.pins = (settings.rgb_red_pin, settings.rgb_green_pin, settings.rgb_blue_pin)
        self.pwms = []
        self.stop_event = threading.Event()
        self.active = False
        self.cycle = tuple(settings.camouflage_cycle)
        self.thread = threading.Thread(target=self._worker, daemon=True)
        for pin in self.pins:
            GPIO.setup(pin, GPIO.OUT)
            pwm = GPIO.PWM(pin, 200)
            pwm.start(0)
            self.pwms.append(pwm)

    def start(self) -> None:
        self.thread.start()

    def set_color(self, rgb_percent: tuple[int, int, int]) -> None:
        for pwm, value in zip(self.pwms, rgb_percent):
            pwm.ChangeDutyCycle(clamp(value, 0, 100))

    def show_named(self, color_name: str) -> None:
        self.set_color(self.COLOR_MAP.get(color_name, (0, 0, 0)))

    def set_active(self, enabled: bool) -> None:
        self.active = enabled
        if not enabled:
            self.show_named('apagado')

    def _worker(self) -> None:
        index = 0
        while not self.stop_event.is_set():
            if self.active:
                self.set_color(self.cycle[index])
                index = (index + 1) % len(self.cycle)
                self.stop_event.wait(0.6)
            else:
                self.stop_event.wait(0.1)
        self.show_named('apagado')

    def cleanup(self) -> None:
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.show_named('apagado')
        for pwm in self.pwms:
            pwm.stop()


class StatusLedPanel:
    def __init__(self, settings) -> None:
        self.green_pin = settings.status_green_pin
        self.yellow_pin = settings.status_yellow_pin
        self.red_pin = settings.status_red_pin
        self.blue_pin = settings.status_blue_pin
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.snapshot_provider: Callable[[], dict] | None = None
        for pin in (self.green_pin, self.yellow_pin, self.red_pin, self.blue_pin):
            if pin is not None:
                GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    def set_snapshot_provider(self, provider: Callable[[], dict]) -> None:
        self.snapshot_provider = provider

    def start(self) -> None:
        self.thread.start()

    def _safe_output(self, pin: int | None, state: bool) -> None:
        if pin is not None:
            GPIO.output(pin, GPIO.HIGH if state else GPIO.LOW)

    def _worker(self) -> None:
        blink = False
        while not self.stop_event.is_set():
            snap = self.snapshot_provider() if self.snapshot_provider else {}
            fire = bool(snap.get('alerts', {}).get('fire', False))
            meteor = snap.get('proximity', {}).get('level', 'none') != 'none'
            camo = bool(snap.get('color', {}).get('camouflageActive', snap.get('camouflage', {}).get('active', False)))
            emergency = bool(snap.get('emergency', False))

            blink = not blink
            self._safe_output(self.green_pin, not emergency)
            self._safe_output(self.yellow_pin, meteor)
            self._safe_output(self.red_pin, blink if fire else False)
            self._safe_output(self.blue_pin, camo)
            self.stop_event.wait(0.35)

        self._safe_output(self.green_pin, False)
        self._safe_output(self.yellow_pin, False)
        self._safe_output(self.red_pin, False)
        self._safe_output(self.blue_pin, False)

    def stop(self) -> None:
        self.stop_event.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)


class ButtonsController:
    """Usa callbacks pequenos y deja el trabajo real fuera del callback."""

    def __init__(self, settings, on_button: Callable[[str], None]) -> None:
        self.on_button = on_button
        self.pin_map = {
            'door_open': settings.button_door_open_pin,
            'door_close': settings.button_door_close_pin,
            'turret_left': settings.button_turret_left_pin,
            'turret_right': settings.button_turret_right_pin,
            'fire': settings.button_fire_pin,
            'emergency': settings.button_emergency_pin,
        }
        for name, pin in self.pin_map.items():
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=self._build_callback(name), bouncetime=150)

    def _build_callback(self, name: str):
        def _callback(channel):
            self.on_button(name)
        return _callback

    def cleanup(self) -> None:
        for pin in self.pin_map.values():
            GPIO.remove_event_detect(pin)
