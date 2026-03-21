"""Pantalla LCD I2C.

Requiere: pip install rpi-lcd
Tambien requiere I2C habilitado en raspi-config.
"""

from __future__ import annotations

import threading
import time

try:
    from rpi_lcd import LCD
except ImportError:  # pragma: no cover
    LCD = None


class LcdService:
    def __init__(self, settings, state, stop_event: threading.Event) -> None:
        self.settings = settings
        self.state = state
        self.stop_event = stop_event
        self.thread = threading.Thread(target=self._worker, daemon=True)
        self.lcd = None
        self._local_stop = threading.Event()
        self._last_lines = ('', '')
        if settings.enable_lcd and LCD is not None:
            try:
                self.lcd = LCD(settings.lcd_address, 1, settings.lcd_cols, settings.lcd_rows, True)
            except Exception as exc:
                print(f'[LCD] Desactivado: {exc}')
                self.lcd = None
        elif settings.enable_lcd:
            print('[LCD] Falta la libreria rpi-lcd.')

    def start(self) -> None:
        if self.lcd is not None:
            self.thread.start()

    def _write(self, line1: str, line2: str) -> None:
        if self.lcd is None:
            return
        line1 = (line1 or '')[: self.settings.lcd_cols].ljust(self.settings.lcd_cols)
        line2 = (line2 or '')[: self.settings.lcd_cols].ljust(self.settings.lcd_cols)
        if (line1, line2) == self._last_lines:
            return
        self.lcd.clear()
        self.lcd.text(line1, 1)
        self.lcd.text(line2, 2)
        self._last_lines = (line1, line2)

    def _worker(self) -> None:
        screen_index = 0
        last_switch = time.monotonic()
        while not (self.stop_event.is_set() or self._local_stop.is_set()):
            snap = self.state.snapshot()
            now = time.monotonic()
            message = self.state.current_message()

            if snap['emergency']:
                lines = ('EMERGENCIA', 'Motores detenidos')
            elif snap['alerts']['fire']:
                lines = ('ALERTA INCENDIO', 'Ventiladores ON')
            elif message:
                lines = ('Mensaje:', message)
            else:
                screens = [
                    (
                        f"T:{snap['environment']['temperature'] or '--'}C",
                        f"H:{snap['environment']['humidity'] or '--'}%",
                    ),
                    (
                        'Meteorito:',
                        f"{snap['proximity']['value'] or '--'} cm",
                    ),
                    (
                        'Torreta:',
                        f"{snap['turret']['angle']} deg",
                    ),
                    (
                        'Estado:',
                        snap['status'],
                    ),
                ]
                if now - last_switch >= self.settings.lcd_screen_period_s:
                    screen_index = (screen_index + 1) % len(screens)
                    last_switch = now
                lines = screens[screen_index]

            self._write(lines[0], lines[1])
            self._local_stop.wait(self.settings.lcd_refresh_s)

        if self.lcd is not None:
            self.lcd.clear()

    def stop(self) -> None:
        self._local_stop.set()
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.lcd is not None:
            self.lcd.clear()
