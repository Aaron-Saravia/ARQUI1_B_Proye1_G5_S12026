# Nave RPi - Core Python

Base en Python para la Raspberry Pi 4 (Raspberry Pi OS 64 bits) del proyecto "Estacion de Control de la Nave".

Esta version sigue una idea practica:
- usa `RPi.GPIO` para GPIO y actuadores,
- usa callbacks para botones y sensor de gas digital,
- usa workers livianos con `threading.Event().wait(...)` para tareas periodicas,
- evita un gran loop principal bloqueante,
- usa MQTT para integracion con backend/dashboard,
- puede escribir a MongoDB de forma directa como apoyo.

## Que cubre

- Sensor de gas MQ-2/MQ-135 por salida digital `DO`
- Sensor HC-SR04
- Sensor DHT11/DHT22
- Sensor de color TCS3200 **o** TCS34725
- Torreta con 28BYJ-48 + ULN2003
- Compuerta con servo SG90
- Ventiladores de incendio
- Buzzer de alertas
- LED laser de disparo
- LEDs RGB para camuflaje
- LCD I2C 16x2 / 20x4
- 6 botones fisicos
- 4 LEDs de estado
- MQTT bidireccional
- MongoDB directo opcional

## Antes de cablear: nota importante de pines

Este proyecto usa muchos GPIO. Para que la Raspberry alcance mejor, este scaffold soporta **TCS34725 por I2C** ademas de TCS3200.

Si usan **TCS34725**, el presupuesto de GPIO mejora mucho porque comparte I2C con el LCD.
Si usan **TCS3200**, revisen bien `starship_rpi/config.py` porque van a consumir mas pines.

## Suposiciones practicas

1. El sensor MQ-2/MQ-135 se lee por salida digital `DO`.
   La Raspberry Pi no puede leer `AO` sin un ADC externo.
2. Los ventiladores se controlan con transistor/relay y una sola linea GPIO.
3. Los LEDs RGB de camuflaje se pueden cablear en paralelo por canal R/G/B.
4. El panel LCD usa backpack I2C tipico `0x27`.
5. El color sensor puede ser:
   - `tcs3200` (GPIO)
   - `tcs34725` (I2C)

## Instalacion

### 1) Paquetes del sistema

```bash
sudo apt update
sudo apt install -y python3-pip python3-rpi.gpio libgpiod2 i2c-tools python3-smbus
```

- `python3-rpi.gpio` se usa para GPIO.
- `libgpiod2` ayuda a las librerias de Adafruit/Blinka para DHT y TCS34725.
- `i2c-tools` sirve para verificar el LCD y el TCS34725 con `i2cdetect -y 1`.

### 2) Habilitar I2C

```bash
sudo raspi-config
```

Luego:
- Interface Options
- I2C
- Enable

### 3) Librerias de Python

```bash
cd nave_rpi_python_v1
python3 -m pip install -r requirements.txt
```

### 4) Variables opcionales

```bash
cp .env.example .env
```

Edita `.env` si quieres cambiar broker, MongoDB o activar/desactivar partes.

## Como correr

### Trabajo final

```bash
python3 app.py
```

### Prueba rapida de hardware

```bash
python3 hardware_smoke_test.py
```

Este script NO es el proyecto final. Solo sirve para confirmar si la Raspberry detecta sensores, LCD, botones y actuadores basicos.

## Ajustes que deben revisar primero

Abre `starship_rpi/config.py` y confirma:
- pines BCM,
- modelo de sensor de color,
- tipo de DHT,
- direccion I2C del LCD,
- umbral del gas digital,
- si usar o no Mongo directo.

## Topics MQTT usados

```text
nave/sensores/gas
nave/sensores/proximidad
nave/sensores/color
nave/sensores/ambiente
nave/actuadores/torreta
nave/actuadores/compuertas
nave/actuadores/ventiladores
nave/actuadores/camuflaje
nave/control/mensajes
nave/control/emergencia
nave/alertas/criticas
nave/estado/general
```

## Comandos MQTT esperados

### Torreta

```json
{"action": "set-angle", "value": 135}
{"action": "left", "value": 10}
{"action": "right", "value": 10}
{"action": "home"}
{"action": "fire"}
{"action": "retract"}
```

### Compuertas

```json
{"action": "open"}
{"action": "close"}
{"action": "toggle"}
```

### Ventiladores

```json
{"action": "on"}
{"action": "off"}
{"action": "auto"}
```

### Camuflaje

```json
{"action": "on"}
{"action": "off"}
```

### Mensaje LCD

```json
{"text": "Alerta en sector 7"}
```

### Emergencia

```json
{"action": "on"}
{"action": "off"}
{"action": "reset"}
```

## Comentario sobre el patron del codigo

Tomando como referencia los ejemplos de clase:
- botones y gas usan eventos/callbacks,
- TCS3200 usa `wait_for_edge(...)` para contar pulsos,
- el programa principal no depende de un gran polling loop,
- las tareas periodicas van en workers pequenos con parada limpia.

## Archivo de prueba de hardware

`hardware_smoke_test.py` hace esto:
- imprime nivel del gas digital,
- intenta leer DHT,
- mide HC-SR04,
- intenta leer color,
- muestra algo en LCD,
- parpadea LEDs de estado,
- mueve un poco el servo,
- mueve un poco la torreta,
- espera pulsaciones de botones unos segundos.

## Recomendacion realista para entrega

Si estan cortos de tiempo:
1. dejen estable HC-SR04,
2. dejen estable el gas digital,
3. dejen LCD + mensajes,
4. dejen servo + torreta por MQTT,
5. dejen TCS34725 si el TCS3200 les consume demasiados pines.
