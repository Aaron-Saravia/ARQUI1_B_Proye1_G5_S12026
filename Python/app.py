"""Entry point del proyecto final de la Raspberry Pi."""

import signal
from starship_rpi.controller import StarshipController


def main() -> None:
    controller = StarshipController()
    controller.start()

    # Sin loop principal grande: el main se queda bloqueado aqui.
    def _handle_stop(signum, frame):
        controller.stop()

    signal.signal(signal.SIGINT, _handle_stop)
    signal.signal(signal.SIGTERM, _handle_stop)

    try:
        controller.wait_forever()
    finally:
        controller.stop()


if __name__ == '__main__':
    main()
