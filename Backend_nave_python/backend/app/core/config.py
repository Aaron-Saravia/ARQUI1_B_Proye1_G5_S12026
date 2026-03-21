from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / '.env')


@dataclass(slots=True)
class Settings:
    app_name: str = os.getenv('APP_NAME', 'nave-backend-python')
    app_env: str = os.getenv('APP_ENV', 'development')
    port: int = int(os.getenv('PORT', '3000'))
    mongodb_uri: str = os.getenv('MONGODB_URI', 'mongodb://127.0.0.1:27017')
    mongodb_db: str = os.getenv('MONGODB_DB', 'nave_espacial')
    mqtt_url: str = os.getenv('MQTT_URL', 'mqtt://127.0.0.1:1883')
    mqtt_user: str = os.getenv('MQTT_USER', '')
    mqtt_password: str = os.getenv('MQTT_PASSWORD', '')
    mqtt_client_id: str = os.getenv('MQTT_CLIENT_ID', 'nave-backend-python')
    cors_origins_raw: str = os.getenv(
        'CORS_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3001'
    )
    allow_degraded_mode: bool = os.getenv('ALLOW_DEGRADED_MODE', 'true').lower() == 'true'
    history_default_hours: int = int(os.getenv('HISTORY_DEFAULT_HOURS', '24'))
    chart_bucket_minutes: int = int(os.getenv('CHART_BUCKET_MINUTES', '5'))
    cors_origins: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.cors_origins = [origin.strip() for origin in self.cors_origins_raw.split(',') if origin.strip()]

    @property
    def mqtt_host(self) -> str:
        parsed = urlparse(self.mqtt_url)
        return parsed.hostname or '127.0.0.1'

    @property
    def mqtt_port(self) -> int:
        parsed = urlparse(self.mqtt_url)
        if parsed.port:
            return parsed.port
        return 8883 if parsed.scheme == 'mqtts' else 1883

    @property
    def mqtt_transport(self) -> str:
        parsed = urlparse(self.mqtt_url)
        if parsed.scheme in {'ws', 'wss'}:
            return 'websockets'
        return 'tcp'


settings = Settings()
