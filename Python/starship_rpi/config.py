"""Configuracion central del proyecto.

Edita este archivo primero si cambiaste pines o sensores.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


TOPICS = {
    'sensors': {
        'gas': 'nave/sensores/gas',
        'proximity': 'nave/sensores/proximidad',
        'color': 'nave/sensores/color',
        'environment': 'nave/sensores/ambiente',
    },
    'actuators': {
        'turret': 'nave/actuadores/torreta',
        'doors': 'nave/actuadores/compuertas',
        'fans': 'nave/actuadores/ventiladores',
        'camouflage': 'nave/actuadores/camuflaje',
    },
    'control': {
        'messages': 'nave/control/mensajes',
        'emergency': 'nave/control/emergencia',
    },
    'alerts': {
        'critical': 'nave/alertas/criticas',
    },
    'state': {
        'general': 'nave/estado/general',
    },
}


SUBSCRIPTIONS = [
    TOPICS['actuators']['turret'],
    TOPICS['actuators']['doors'],
    TOPICS['actuators']['fans'],
    TOPICS['actuators']['camouflage'],
    TOPICS['control']['messages'],
    TOPICS['control']['emergency'],
]


def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value not in (None, '') else default


def env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value not in (None, '') else default


@dataclass(slots=True)
class Settings:
    device_id: str = os.getenv('MQTT_CLIENT_ID', 'rpi-nave-01')

    # MQTT
    mqtt_host: str = os.getenv('MQTT_HOST', 'localhost')
    mqtt_port: int = env_int('MQTT_PORT', 1883)
    mqtt_username: str = os.getenv('MQTT_USERNAME', '')
    mqtt_password: str = os.getenv('MQTT_PASSWORD', '')
    mqtt_keepalive: int = 60

    # MongoDB directo opcional.
    enable_direct_mongo: bool = env_bool('ENABLE_DIRECT_MONGO', False)
    mongodb_uri: str = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    mongodb_db: str = os.getenv('MONGODB_DB', 'nave_db')

    # Flags practicos para pruebas por fases.
    enable_lcd: bool = env_bool('ENABLE_LCD', True)
    enable_dht: bool = env_bool('ENABLE_DHT', True)
    enable_gas: bool = env_bool('ENABLE_GAS', True)
    enable_proximity: bool = env_bool('ENABLE_PROXIMITY', True)
    enable_color: bool = env_bool('ENABLE_COLOR', True)
    enable_turret: bool = env_bool('ENABLE_TURRET', True)
    enable_doors: bool = env_bool('ENABLE_DOORS', True)
    enable_rgb: bool = env_bool('ENABLE_RGB', True)
    enable_status_leds: bool = env_bool('ENABLE_STATUS_LEDS', True)
    enable_buttons: bool = env_bool('ENABLE_BUTTONS', True)
    enable_fans: bool = env_bool('ENABLE_FANS', True)
    enable_buzzer: bool = env_bool('ENABLE_BUZZER', True)

    # Modelo de color.
    color_sensor_model: str = os.getenv('COLOR_SENSOR_MODEL', 'tcs34725').strip().lower()
    dht_model: str = os.getenv('DHT_MODEL', 'dht11').strip().lower()
    gas_active_high: bool = env_bool('GAS_ACTIVE_HIGH', False)

    # Intervals.
    dht_period_s: float = env_float('DHT_PERIOD_S', 5.0)
    proximity_period_s: float = env_float('PROXIMITY_PERIOD_S', 0.8)
    color_period_s: float = env_float('COLOR_PERIOD_S', 1.0)
    telemetry_period_s: float = env_float('TELEMETRY_PERIOD_S', 1.0)
    lcd_refresh_s: float = env_float('LCD_REFRESH_S', 0.25)
    lcd_screen_period_s: float = env_float('LCD_SCREEN_PERIOD_S', 3.0)
    lcd_message_hold_s: float = env_float('LCD_MESSAGE_HOLD_S', 5.0)

    # Umbrales del proyecto.
    meteor_far_cm: float = env_float('METEOR_FAR_CM', 50.0)
    meteor_critical_cm: float = env_float('METEOR_CRITICAL_CM', 20.0)
    meteor_max_cm: float = env_float('METEOR_MAX_CM', 120.0)
    temp_high_c: float = env_float('TEMP_HIGH_C', 35.0)
    temp_low_c: float = env_float('TEMP_LOW_C', 10.0)

    # LCD I2C.
    lcd_address: int = int(os.getenv('LCD_ADDRESS', '0x27'), 16)
    lcd_cols: int = env_int('LCD_COLS', 16)
    lcd_rows: int = env_int('LCD_ROWS', 2)

    # DHT.
    dht_pin: int = env_int('DHT_PIN', 4)

    # Gas digital.
    gas_pin: int = env_int('GAS_PIN', 5)

    # HC-SR04.
    trig_pin: int = env_int('TRIG_PIN', 23)
    echo_pin: int = env_int('ECHO_PIN', 24)
    hc_timeout_s: float = env_float('HC_TIMEOUT_S', 0.02)
    hc_samples: int = env_int('HC_SAMPLES', 3)

    # TCS3200. OJO: si cambias a este modelo debes revisar el mapa de pines.
    # Los defaults de abajo son una guia, no un mandato.
    tcs3200_s0_pin: int = env_int('TCS3200_S0_PIN', 0)
    tcs3200_s1_pin: int = env_int('TCS3200_S1_PIN', 14)
    tcs3200_s2_pin: int = env_int('TCS3200_S2_PIN', 15)
    tcs3200_s3_pin: int = env_int('TCS3200_S3_PIN', 8)
    tcs3200_out_pin: int = env_int('TCS3200_OUT_PIN', 9)
    tcs3200_measure_s: float = env_float('TCS3200_MEASURE_S', 0.15)

    # Stepper torreta.
    stepper_pins: tuple[int, int, int, int] = (
        env_int('STEPPER_IN1_PIN', 6),
        env_int('STEPPER_IN2_PIN', 13),
        env_int('STEPPER_IN3_PIN', 19),
        env_int('STEPPER_IN4_PIN', 26),
    )
    stepper_step_delay_s: float = env_float('STEPPER_STEP_DELAY_S', 0.0015)
    stepper_steps_per_rev: int = env_int('STEPPER_STEPS_PER_REV', 4096)

    # Servo compuerta.
    servo_pin: int = env_int('SERVO_PIN', 18)
    servo_open_angle: int = env_int('SERVO_OPEN_ANGLE', 95)
    servo_closed_angle: int = env_int('SERVO_CLOSED_ANGLE', 10)

    # Ventiladores. Por practicidad ambos pueden ir al mismo pin.
    fan_pins: tuple[int, ...] = (
        env_int('FAN1_PIN', 12),
    )

    # Buzzer y LED laser.
    buzzer_pin: int = env_int('BUZZER_PIN', 16)
    shot_led_pin: int = env_int('SHOT_LED_PIN', 25)

    # RGB de camuflaje. Cableados en paralelo por canal.
    rgb_red_pin: int = env_int('RGB_RED_PIN', 14)
    rgb_green_pin: int = env_int('RGB_GREEN_PIN', 15)
    rgb_blue_pin: int = env_int('RGB_BLUE_PIN', 7)

    # LEDs de panel. Si algun pin no les conviene, cambienlo aqui.
    status_green_pin: int = env_int('STATUS_GREEN_PIN', 10)
    status_yellow_pin: int | None = env_int('STATUS_YELLOW_PIN', 11)
    status_red_pin: int = env_int('STATUS_RED_PIN', 8)
    status_blue_pin: int | None = env_int('STATUS_BLUE_PIN', 9)

    # Botones fisicos. Pull-up interno: boton a GND.
    # Este mapa default esta pensado para TCS34725.
    button_door_open_pin: int = env_int('BUTTON_DOOR_OPEN_PIN', 17)
    button_door_close_pin: int = env_int('BUTTON_DOOR_CLOSE_PIN', 27)
    button_turret_left_pin: int = env_int('BUTTON_TURRET_LEFT_PIN', 22)
    button_turret_right_pin: int = env_int('BUTTON_TURRET_RIGHT_PIN', 21)
    button_fire_pin: int = env_int('BUTTON_FIRE_PIN', 20)
    button_emergency_pin: int = env_int('BUTTON_EMERGENCY_PIN', 1)

    # Secuencia correcta del camuflaje.
    camouflage_sequence: tuple[str, str, str] = ('rojo', 'amarillo', 'azul')
    camouflage_cycle: tuple[tuple[int, int, int], ...] = (
        (100, 0, 0),
        (100, 65, 0),
        (0, 0, 100),
    )

    def color_sensor_is_tcs34725(self) -> bool:
        return self.color_sensor_model == 'tcs34725'
