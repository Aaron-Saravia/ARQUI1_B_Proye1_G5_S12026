#!/usr/bin/env python3
"""
Lectura rapida de sensores para Raspberry Pi 4.
- Muestra datos en LCD I2C 16x2/20x4
- Lee MQ-2 (salida digital DO)
- Lee HC-SR04
- Lee sensor de humedad de suelo (salida digital DO)
- Lee DHT11
- Guarda todo en un .txt en formato JSON Lines

Numeracion usada: BCM.

IMPORTANTE:
- LCD I2C y DHT11 son compatibles con Raspberry Pi 4.
- MQ-2 y muchos sensores de suelo suelen conectarse por salida digital DO.
- Si tu sensor de suelo o MQ-2 lo quieres leer por AO (analogico), la Raspberry NO puede leerlo directo.
  Necesitarias un ADC externo, por ejemplo MCP3008 o ADS1115.
- HC-SR04: el pin ECHO debe entrar a la Raspberry con divisor de voltaje.
"""

from __future__ import annotations

import json
import signal
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import RPi.GPIO as GPIO

# Requiere: pip install adafruit-blinka adafruit-circuitpython-dht
import adafruit_dht
import board

# Requiere: pip install RPLCD smbus2
from RPLCD.i2c import CharLCD


# =========================
# Configuracion rapida
# =========================
LCD_ADDRESS = 0x27          # Cambia a 0x3F si tu LCD usa otra direccion
LCD_COLS = 16
LCD_ROWS = 2

MQ2_DO_PIN = 5              # MQ-2 salida digital DO
TRIG_PIN = 23               # HC-SR04 TRIG
ECHO_PIN = 24               # HC-SR04 ECHO
SOIL_DO_PIN = 17            # Humedad de suelo salida digital DO
DHT_GPIO_BCM = 4            # DHT11 en GPIO4

LOG_FILE = Path("lecturas_sensores.txt")

# Intervalos sin bucle apretado.
MQ2_INTERVAL = 2.0
HC_SR04_INTERVAL = 2.0
SOIL_INTERVAL = 5.0
DHT_INTERVAL = 5.0          # El enunciado pide 5 segundos para ambiente
LCD_INTERVAL = 3.0


# =========================
# Estado compartido
# =========================
@dataclass
class SharedState:
    gas_detected: bool | None = None
    soil_dry: bool | None = None
    distance_cm: float | None = None
    temperature_c: float | None = None
    humidity_pct: float | None = None
    last_error: str = ""


state = SharedState()
state_lock = threading.Lock()
stop_event = threading.Event()
threads: list[threading.Timer] = []


# =========================
# Utilidades
# =========================
def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def log_line(sensor: str, data: dict[str, Any]) -> None:
    """Guarda una linea JSON en el .txt."""
    row = {
        "timestamp": now_iso(),
        "sensor": sensor,
        "data": data,
    }
    with LOG_FILE.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_float(value: Any, decimals: int = 2) -> float | None:
    if value is None:
        return None
    return round(float(value), decimals)


# =========================
# LCD
# =========================
def init_lcd() -> CharLCD:
    """Inicializa LCD I2C tipo PCF8574."""
    # Si falla aqui, revisa: sudo raspi-config -> Interface Options -> I2C
    lcd = CharLCD(
        i2c_expander="PCF8574",
        address=LCD_ADDRESS,
        port=1,
        cols=LCD_COLS,
        rows=LCD_ROWS,
        dotsize=8,
        charmap="A00",
        auto_linebreaks=False,
    )
    lcd.clear()
    lcd.write_string("Sistema listo")
    return lcd


# =========================
# Sensores
# =========================
def init_gpio() -> None:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    GPIO.setup(MQ2_DO_PIN, GPIO.IN)
    GPIO.setup(SOIL_DO_PIN, GPIO.IN)

    GPIO.setup(TRIG_PIN, GPIO.OUT)
    GPIO.setup(ECHO_PIN, GPIO.IN)
    GPIO.output(TRIG_PIN, False)


def read_mq2_digital() -> bool:
    """True = gas detectado si el DO del modulo cae a LOW."""
    return GPIO.input(MQ2_DO_PIN) == GPIO.LOW


def read_soil_digital() -> bool:
    """True = suelo seco si el DO del modulo cae a LOW."""
    return GPIO.input(SOIL_DO_PIN) == GPIO.LOW


def read_distance_cm() -> float | None:
    """Lee HC-SR04 con timeouts para no bloquear el programa."""
    GPIO.output(TRIG_PIN, False)
    time.sleep(0.0002)

    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, False)

    start_wait = time.perf_counter()
    while GPIO.input(ECHO_PIN) == 0:
        pulse_start = time.perf_counter()
        if pulse_start - start_wait > 0.03:
            return None

    start_high = time.perf_counter()
    while GPIO.input(ECHO_PIN) == 1:
        pulse_end = time.perf_counter()
        if pulse_end - start_high > 0.03:
            return None

    pulse_duration = pulse_end - pulse_start
    distance_cm = (pulse_duration * 34300) / 2
    return round(distance_cm, 2)


# use_pulseio=False evita problemas comunes en Raspberry Pi.
DHT_PIN_BOARD = getattr(board, f'D{DHT_GPIO_BCM}')
dht = adafruit_dht.DHT11(DHT_PIN_BOARD, use_pulseio=False)


def read_dht11() -> tuple[float | None, float | None]:
    """DHT11 puede fallar esporadicamente; por eso se captura RuntimeError."""
    try:
        temperature_c = dht.temperature
        humidity_pct = dht.humidity
        return safe_float(temperature_c, 1), safe_float(humidity_pct, 1)
    except RuntimeError:
        return None, None
    except Exception:
        return None, None


# =========================
# Tareas programadas
# =========================
def schedule_every(seconds: float, func) -> None:
    """Programa una tarea recurrente sin usar un while True apretado."""
    if stop_event.is_set():
        return

    timer = threading.Timer(seconds, run_and_reschedule, args=(seconds, func))
    timer.daemon = True
    threads.append(timer)
    timer.start()


def run_and_reschedule(seconds: float, func) -> None:
    if stop_event.is_set():
        return
    try:
        func()
    finally:
        schedule_every(seconds, func)


def task_mq2() -> None:
    detected = read_mq2_digital()
    with state_lock:
        state.gas_detected = detected
    log_line("mq2", {"gas_detected": detected})


def task_soil() -> None:
    dry = read_soil_digital()
    with state_lock:
        state.soil_dry = dry
    log_line("soil", {"soil_dry": dry})


def task_hcsr04() -> None:
    distance = read_distance_cm()
    with state_lock:
        state.distance_cm = distance
    log_line("hc_sr04", {"distance_cm": distance})


def task_dht11() -> None:
    temperature_c, humidity_pct = read_dht11()
    with state_lock:
        if temperature_c is not None:
            state.temperature_c = temperature_c
        if humidity_pct is not None:
            state.humidity_pct = humidity_pct
    log_line(
        "dht11",
        {
            "temperature_c": temperature_c,
            "humidity_pct": humidity_pct,
        },
    )


lcd_pages = [0]


def task_lcd() -> None:
    """Rota mensajes simples en LCD."""
    with state_lock:
        gas = state.gas_detected
        soil = state.soil_dry
        dist = state.distance_cm
        temp = state.temperature_c
        hum = state.humidity_pct

    page = lcd_pages[0] % 3
    lcd.clear()

    if page == 0:
        line1 = f"Temp:{temp if temp is not None else '--'}C"
        line2 = f"Hum:{hum if hum is not None else '--'}%"
    elif page == 1:
        line1 = f"Dist:{dist if dist is not None else '--'}cm"
        line2 = f"Gas:{'ALERTA' if gas else 'OK'}"
    else:
        line1 = "Suelo:" + ("SECO" if soil else "OK") if soil is not None else "Suelo:--"
        line2 = now_iso()[11:19]

    lcd.write_string(line1[:LCD_COLS])
    if LCD_ROWS > 1:
        lcd.cursor_pos = (1, 0)
        lcd.write_string(line2[:LCD_COLS])

    lcd_pages[0] += 1


# =========================
# Inicio y cierre
# =========================
def write_header() -> None:
    if not LOG_FILE.exists():
        with LOG_FILE.open("w", encoding="utf-8") as fh:
            fh.write("# lecturas de sensores - una linea JSON por lectura\n")


def shutdown(*_args) -> None:
    stop_event.set()
    for timer in threads:
        try:
            timer.cancel()
        except Exception:
            pass

    try:
        lcd.clear()
        lcd.write_string("Apagando...")
    except Exception:
        pass

    try:
        dht.exit()
    except Exception:
        pass

    GPIO.cleanup()
    sys.exit(0)


write_header()
init_gpio()
lcd = init_lcd()

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# Disparo inicial.
task_mq2()
task_hcsr04()
task_soil()
task_dht11()
task_lcd()

# Repeticiones.
schedule_every(MQ2_INTERVAL, task_mq2)
schedule_every(HC_SR04_INTERVAL, task_hcsr04)
schedule_every(SOIL_INTERVAL, task_soil)
schedule_every(DHT_INTERVAL, task_dht11)
schedule_every(LCD_INTERVAL, task_lcd)

print("Leyendo sensores. Guardando en:", LOG_FILE.resolve())
print("Ctrl+C para salir.")

# Espera pasiva. No usa bucle while apretado.
signal.pause()