# Entregable integrado: frontend + backend Python

Este paquete deja el **frontend trabajado** y agrega un **backend completamente en Python** para cumplir con el enunciado:

- API REST para frontend y persistencia.
- Socket.IO para tiempo real.
- MQTT para comunicación con Raspberry Pi.
- MongoDB para telemetría, eventos, comandos y mensajes.

## Carpetas

- `frontend/` → dashboard trabajado
- `backend/` → nueva API en Python

## Puertos por defecto

- Frontend Vite: `5173`
- Backend FastAPI + Socket.IO: `3000`
- MongoDB: `27017`
- Mosquitto MQTT: `1883`

## Flujo

```text
Raspberry Pi -> MQTT -> Backend Python -> MongoDB
                                  -> Socket.IO -> Frontend
Frontend -> API REST -> Backend Python -> MQTT / MongoDB
```

## Inicio rápido

### Backend

```bash
cd backend
docker compose up -d
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python run.py
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Nota

El backend se diseñó para ser compatible con el frontend trabajado y además con el scaffold original del proyecto.
