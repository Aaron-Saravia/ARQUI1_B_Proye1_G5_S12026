"""Prueba rapida de hardware.

No es el proyecto final.
Sirve para revisar si la Raspberry ve sensores y actuadores basicos.
"""

import threading
import time

import RPi.GPIO as GPIO

from starship_rpi.config import Settings
from starship_rpi.hardware import (
    AlertBuzzer,
    ButtonsController,
    FansController,
    LaserLed,
    RgbCamouflage,
    ServoDoor,
    StepperTurret,
    StatusLedPanel,
)
from starship_rpi.display import LcdService
from starship_rpi.sensors import (
    DhtWorker,
    GasSensorDigital,
    ProximityWorker,
    TCS3200Worker,
    TCS34725Worker,
)
from starship_rpi.state import SharedState
from starship_rpi.utils import safe_run


class SmokeTest:
    def __init__(self) -> None:
        self.settings = Settings()
        self.stop_event = threading.Event()
        self.state = SharedState(self.settings.device_id)
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

    def run(self) -> None:
        print('== Smoke test ==')
        print('Recuerda editar config.py si cambiaste pines.')

        self._test_status_leds()
        self._test_lcd()
        self._test_gas_once()
        self._test_dht_once()
        self._test_proximity_once()
        self._test_color_once()
        self._test_servo_once()
        self._test_turret_once()
        self._test_fans_buzzer_once()
        self._test_buttons_window()
        print('Smoke test terminado.')

    def _test_status_leds(self) -> None:
        if not self.settings.enable_status_leds:
            return
        print('[LEDs] Probando panel de estado...')
        panel = StatusLedPanel(self.settings)
        panel.set_snapshot_provider(
            lambda: {
                'alerts': {'fire': False},
                'proximity': {'level': 'none'},
                'camouflage': {'active': False},
                'emergency': False,
            }
        )
        time.sleep(0.1)
        GPIO.output(self.settings.status_green_pin, GPIO.HIGH)
        time.sleep(0.4)
        if self.settings.status_yellow_pin is not None:
            GPIO.output(self.settings.status_yellow_pin, GPIO.HIGH)
            time.sleep(0.4)
        GPIO.output(self.settings.status_red_pin, GPIO.HIGH)
        time.sleep(0.4)
        if self.settings.status_blue_pin is not None:
            GPIO.output(self.settings.status_blue_pin, GPIO.HIGH)
            time.sleep(0.4)
        panel.stop()

    def _test_lcd(self) -> None:
        if not self.settings.enable_lcd:
            return
        print('[LCD] Mostrando texto de prueba...')
        lcd = LcdService(self.settings, self.state, self.stop_event)
        lcd.start()
        self.state.set_message('LCD OK - prueba', 'smoke-test')
        time.sleep(2.0)
        lcd.stop()

    def _test_gas_once(self) -> None:
        if not self.settings.enable_gas:
            return
        print('[GAS] Leyendo estado digital...')
        sensor = GasSensorDigital(self.settings, lambda danger: print(f'Gas danger: {danger}'))
        print(f'Gas actual: {sensor.is_danger()}')
        sensor.cleanup()

    def _test_dht_once(self) -> None:
        if not self.settings.enable_dht:
            return
        print('[DHT] Intentando leer ambiente...')
        result = {}

        def _on_read(temp, hum):
            result['temp'] = temp
            result['hum'] = hum
            print(f'Temp={temp:.1f}C Hum={hum:.1f}%')

        worker = DhtWorker(self.settings, self.stop_event, _on_read)
        worker.start()
        time.sleep(4.5)
        self.stop_event.set()
        worker.stop()
        self.stop_event.clear()
        if not result:
            print('DHT sin lectura valida en la ventana de prueba.')

    def _test_proximity_once(self) -> None:
        if not self.settings.enable_proximity:
            return
        print('[HC-SR04] Midiendo distancia...')

        def _on_read(distance):
            if distance is None:
                print('Distancia invalida')
            else:
                print(f'Distancia={distance:.1f} cm')

        worker = ProximityWorker(self.settings, self.stop_event, _on_read)
        worker.start()
        time.sleep(2.5)
        self.stop_event.set()
        worker.stop()
        self.stop_event.clear()

    def _test_color_once(self) -> None:
        if not self.settings.enable_color:
            return
        print('[COLOR] Intentando detectar color...')

        def _on_read(color_name, rgb_or_norm):
            print(f'Color={color_name} data={rgb_or_norm}')

        if self.settings.color_sensor_model == 'tcs34725':
            worker = TCS34725Worker(self.settings, self.stop_event, _on_read)
        else:
            worker = TCS3200Worker(self.settings, self.stop_event, _on_read)
        worker.start()
        time.sleep(3.0)
        self.stop_event.set()
        worker.stop()
        self.stop_event.clear()

    def _test_servo_once(self) -> None:
        if not self.settings.enable_doors:
            return
        print('[SERVO] Abriendo y cerrando compuerta...')
        door = ServoDoor(self.settings)
        door.open()
        time.sleep(0.8)
        door.close()
        door.cleanup()

    def _test_turret_once(self) -> None:
        if not self.settings.enable_turret:
            return
        print('[TURRET] Giro corto izquierda/derecha...')
        turret = StepperTurret(self.settings)
        turret.nudge_left(8)
        turret.nudge_right(8)
        turret.cleanup()

    def _test_fans_buzzer_once(self) -> None:
        if self.settings.enable_fans:
            print('[FANS] Encendiendo ventilador(es) 1 segundo...')
            fans = FansController(self.settings)
            fans.set_on(True)
            time.sleep(1.0)
            fans.set_on(False)
            fans.cleanup()
        if self.settings.enable_buzzer:
            print('[BUZZER/LASER] Patrons cortos...')
            buzzer = AlertBuzzer(self.settings)
            buzzer.start()
            buzzer.set_mode('near')
            time.sleep(1.5)
            buzzer.set_mode('off')
            buzzer.stop()
            laser = LaserLed(self.settings)
            laser.pulse(0.25)
            laser.cleanup()

    def _test_buttons_window(self) -> None:
        if not self.settings.enable_buttons:
            return
        print('[BUTTONS] Tienes 10 segundos para presionar botones...')
        received = []

        def _on_button(name):
            print(f'Boton detectado: {name}')
            received.append(name)

        buttons = ButtonsController(self.settings, _on_button)
        time.sleep(10.0)
        buttons.cleanup()
        if not received:
            print('No se detectaron botones en la ventana de prueba.')


if __name__ == '__main__':
    test = SmokeTest()
    safe_run(test.run, cleanup=GPIO.cleanup)
