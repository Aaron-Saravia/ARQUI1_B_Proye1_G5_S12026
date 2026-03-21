"""Sensores del proyecto."""

from __future__ import annotations

import statistics
import threading
import time
from typing import Callable

import RPi.GPIO as GPIO

from .utils import clamp

# Requiere: pip install adafruit-circuitpython-dht Adafruit-Blinka
# y tambien: sudo apt install libgpiod2
try:
    import adafruit_dht
    import board
except ImportError:  # pragma: no cover
    adafruit_dht = None
    board = None

# Requiere: pip install adafruit-circuitpython-tcs34725 Adafruit-Blinka
try:
    import adafruit_tcs34725
except ImportError:  # pragma: no cover
    adafruit_tcs34725 = None


def classify_color_from_rgb(r: int, g: int, b: int) -> str:
    total = max(r + g + b, 1)
    nr = r / total
    ng = g / total
    nb = b / total

    if nr > 0.42 and ng < 0.33 and nb < 0.28:
        return 'rojo'
    if ng > 0.42 and nr < 0.36 and nb < 0.28:
        return 'verde'
    if nb > 0.42 and nr < 0.30 and ng < 0.35:
        return 'azul'
    if nr > 0.33 and ng > 0.33 and nb < 0.20:
        return 'amarillo'
    return 'desconocido'


class GasSensorDigital:
    def __init__(self, settings, on_change: Callable[[bool], None]) -> None:
        self.pin = settings.gas_pin
        self.active_high = settings.gas_active_high
        self.on_change = on_change
        GPIO.setup(self.pin, GPIO.IN)
        GPIO.add_event_detect(self.pin, GPIO.BOTH, callback=self._edge_callback, bouncetime=120)

    def is_danger(self) -> bool:
        level = GPIO.input(self.pin)
        return bool(level == GPIO.HIGH) if self.active_high else bool(level == GPIO.LOW)

    def _edge_callback(self, channel):
        self.on_change(self.is_danger())

    def cleanup(self) -> None:
        GPIO.remove_event_detect(self.pin)


class DhtWorker:
    def __init__(self, settings, stop_event: threading.Event, on_read: Callable[[float, float], None]) -> None:
        self.settings = settings
        self.stop_event = stop_event
        self.on_read = on_read
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.sensor = None
        self.last_ok = None
        self.errors = 0

        if adafruit_dht is not None and board is not None:
            pin = getattr(board, f'D{settings.dht_pin}')
            if settings.dht_model == 'dht22':
                self.sensor = adafruit_dht.DHT22(pin)
            else:
                self.sensor = adafruit_dht.DHT11(pin)
        else:
            print('[DHT] Librerias Adafruit no instaladas.')

    def start(self) -> None:
        if self.sensor is not None:
            self.thread.start()

    def _worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                temperature = self.sensor.temperature
                humidity = self.sensor.humidity
                if temperature is None or humidity is None:
                    raise RuntimeError('Lectura nula')
                self.last_ok = (float(temperature), float(humidity))
                self.errors = 0
                self.on_read(float(temperature), float(humidity))
            except RuntimeError:
                self.errors += 1
                if self.errors >= 8:
                    try:
                        self.sensor.exit()
                    except Exception:
                        pass
                    time.sleep(1.0)
                    pin = getattr(board, f'D{self.settings.dht_pin}')
                    if self.settings.dht_model == 'dht22':
                        self.sensor = adafruit_dht.DHT22(pin)
                    else:
                        self.sensor = adafruit_dht.DHT11(pin)
                    self.errors = 0
            self.stop_event.wait(self.settings.dht_period_s)

    def stop(self) -> None:
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.sensor is not None:
            try:
                self.sensor.exit()
            except Exception:
                pass


class ProximityWorker:
    SPEED_OF_SOUND_CM_S = 34300

    def __init__(self, settings, stop_event: threading.Event, on_read: Callable[[float | None], None]) -> None:
        self.settings = settings
        self.stop_event = stop_event
        self.on_read = on_read
        self.thread = threading.Thread(target=self._worker, daemon=True)
        GPIO.setup(settings.trig_pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(settings.echo_pin, GPIO.IN)

    def start(self) -> None:
        self.thread.start()

    def _single_read(self) -> float | None:
        GPIO.output(self.settings.trig_pin, GPIO.LOW)
        time.sleep(0.0002)
        GPIO.output(self.settings.trig_pin, GPIO.HIGH)
        time.sleep(0.00001)
        GPIO.output(self.settings.trig_pin, GPIO.LOW)

        start_time = time.time()
        while GPIO.input(self.settings.echo_pin) == GPIO.LOW:
            if time.time() - start_time > self.settings.hc_timeout_s:
                return None

        pulse_start = time.time()
        while GPIO.input(self.settings.echo_pin) == GPIO.HIGH:
            if time.time() - pulse_start > self.settings.hc_timeout_s:
                return None

        pulse_end = time.time()
        duration = pulse_end - pulse_start
        return (duration * self.SPEED_OF_SOUND_CM_S) / 2.0

    def _worker(self) -> None:
        while not self.stop_event.is_set():
            samples: list[float] = []
            for _ in range(self.settings.hc_samples):
                value = self._single_read()
                if value is not None:
                    samples.append(value)
                time.sleep(0.03)
            if samples:
                self.on_read(statistics.median(samples))
            else:
                self.on_read(None)
            self.stop_event.wait(self.settings.proximity_period_s)

    def stop(self) -> None:
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)


class TCS3200Worker:
    FILTERS = {
        'red': (0, 0),
        'blue': (0, 1),
        'clear': (1, 0),
        'green': (1, 1),
    }

    def __init__(self, settings, stop_event: threading.Event, on_read: Callable[[str, dict], None]) -> None:
        self.settings = settings
        self.stop_event = stop_event
        self.on_read = on_read
        self.thread = threading.Thread(target=self._worker, daemon=True)
        for pin in (
            settings.tcs3200_s0_pin,
            settings.tcs3200_s1_pin,
            settings.tcs3200_s2_pin,
            settings.tcs3200_s3_pin,
        ):
            GPIO.setup(pin, GPIO.OUT)
        GPIO.setup(settings.tcs3200_out_pin, GPIO.IN)
        GPIO.output(settings.tcs3200_s0_pin, GPIO.HIGH)
        GPIO.output(settings.tcs3200_s1_pin, GPIO.LOW)

    def start(self) -> None:
        self.thread.start()

    def _set_filter(self, name: str) -> None:
        s2, s3 = self.FILTERS[name]
        GPIO.output(self.settings.tcs3200_s2_pin, s2)
        GPIO.output(self.settings.tcs3200_s3_pin, s3)

    def _count_pulses(self, duration_s: float) -> int:
        count = 0
        end_time = time.monotonic() + duration_s
        while time.monotonic() < end_time:
            remaining_ms = int((end_time - time.monotonic()) * 1000)
            if remaining_ms <= 0:
                break
            if GPIO.wait_for_edge(self.settings.tcs3200_out_pin, GPIO.RISING, timeout=remaining_ms):
                count += 1
        return count

    def _read_frequency(self) -> float:
        pulses = self._count_pulses(self.settings.tcs3200_measure_s)
        return pulses / self.settings.tcs3200_measure_s

    def _worker(self) -> None:
        while not self.stop_event.is_set():
            freqs = {}
            for name in ('red', 'green', 'blue'):
                self._set_filter(name)
                time.sleep(0.05)
                freqs[name] = self._read_frequency()
            total = max(freqs['red'] + freqs['green'] + freqs['blue'], 1.0)
            rgb_norm = {
                'r': round(freqs['red'] / total, 3),
                'g': round(freqs['green'] / total, 3),
                'b': round(freqs['blue'] / total, 3),
            }
            color_name = classify_color_from_rgb(
                int(rgb_norm['r'] * 255),
                int(rgb_norm['g'] * 255),
                int(rgb_norm['b'] * 255),
            )
            self.on_read(color_name, {'normalized': rgb_norm, 'freqs': freqs})
            self.stop_event.wait(self.settings.color_period_s)

    def stop(self) -> None:
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)


class TCS34725Worker:
    def __init__(self, settings, stop_event: threading.Event, on_read: Callable[[str, dict], None]) -> None:
        self.settings = settings
        self.stop_event = stop_event
        self.on_read = on_read
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.sensor = None
        if adafruit_tcs34725 is None or board is None:
            print('[TCS34725] Libreria no instalada.')
            return
        try:
            i2c = board.I2C()
            self.sensor = adafruit_tcs34725.TCS34725(i2c)
            self.sensor.integration_time = 50
            self.sensor.gain = 4
        except Exception as exc:
            print(f'[TCS34725] Desactivado: {exc}')
            self.sensor = None

    def start(self) -> None:
        if self.sensor is not None:
            self.thread.start()

    def _worker(self) -> None:
        while not self.stop_event.is_set():
            try:
                r, g, b = self.sensor.color_rgb_bytes
                color_name = classify_color_from_rgb(r, g, b)
                self.on_read(color_name, {'rgb': {'r': r, 'g': g, 'b': b}})
            except Exception as exc:
                print(f'[TCS34725] Error de lectura: {exc}')
            self.stop_event.wait(self.settings.color_period_s)

    def stop(self) -> None:
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
