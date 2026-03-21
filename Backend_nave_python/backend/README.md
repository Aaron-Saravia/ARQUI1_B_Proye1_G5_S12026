# Backend Python para la Nave Espacial

Este backend reemplaza el backend en Node.js por una implementación en **Python + FastAPI + Socket.IO + MQTT + MongoDB**.

## Qué hace

- Expone una API REST para el frontend.
- Recibe telemetría desde MQTT.
- Guarda lecturas, eventos, comandos y mensajes en MongoDB.
- Empuja actualizaciones en tiempo real al dashboard por Socket.IO.
- Es compatible con:
  - el frontend `Andy`
  - el scaffold original del backend/frontend

## Stack

- FastAPI
- python-socketio
- PyMongo
- paho-mqtt
- Uvicorn

## Estructura

```text
backend/
  app/
    api/routes/
    core/
    db/
    services/
  docker/
  .env.example
  docker-compose.yml
  demo_publisher.py
  requirements.txt
  run.py
```

## Pasos de ejecución

### 1) Levantar MongoDB y Mosquitto

Con Docker:

```bash
cd backend
docker compose up -d
```

### 2) Crear entorno e instalar dependencias

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3) Ejecutar el backend

```bash
python run.py
```

El servidor queda en:

```text
http://localhost:3000
```

## Endpoint principales

### Compatibles con tu frontend trabajado

- `GET /api/sensores/historial`
- `GET /api/estadisticas`
- `POST /api/comandos`

Payload esperado por `/api/comandos`:

```json
{ "comando": "torreta", "valor": 120 }
```

Ejemplos soportados:

```json
{ "comando": "torreta", "valor": 180 }
{ "comando": "compuerta", "valor": "Abrir" }
{ "comando": "camuflaje", "valor": "activar" }
{ "comando": "lcd", "valor": "Mensaje para la sala" }
{ "comando": "emergencia", "valor": true }
```

### Compatibles con el scaffold original

- `GET /api/health`
- `GET /api/sensors/latest`
- `GET /api/sensors/history?type=gas&hours=24`
- `GET /api/events`
- `GET /api/messages`
- `POST /api/messages`
- `POST /api/commands`
- `GET /api/stats`

## Eventos Socket.IO

El frontend `Andy` escucha este evento:

- `telemetria_actualizada`

También se emiten eventos más detallados:

- `sensor:update`
- `state:update`
- `actuator:update`
- `command:sent`
- `message:new`
- `event:new`

## MQTT

### Topics suscritos

- `nave/sensores/gas`
- `nave/sensores/proximidad`
- `nave/sensores/color`
- `nave/sensores/ambiente`
- `nave/alertas/criticas`
- `nave/estado/general`

### Topics publicados por comandos

- `nave/actuadores/torreta`
- `nave/actuadores/compuertas`
- `nave/actuadores/ventiladores`
- `nave/actuadores/camuflaje`
- `nave/control/emergencia`
- `nave/control/mensajes`

## Probar sin Raspberry Pi

Puedes simular telemetría con:

```bash
python demo_publisher.py
```

Eso publica gas, meteoritos, ambiente y color cada 5 segundos.

## Colecciones MongoDB

- `sensor_readings`
- `events`
- `commands`
- `messages`

## Nota

Si MongoDB o MQTT no están disponibles y `ALLOW_DEGRADED_MODE=true`, el backend igual arranca para facilitar pruebas del frontend. En ese modo no habrá persistencia real ni publicación MQTT.
