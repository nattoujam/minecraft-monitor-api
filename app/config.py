from __future__ import annotations

import os
from typing import Optional

import yaml
from pydantic import BaseModel


class ServerConfig(BaseModel):
    code: str
    name: str
    host: str
    port: int = 25565
    start_command: str
    stop_command: str
    mock_ctrl_url: Optional[str] = None


class ApiConfig(BaseModel):
    frontend_origin: str
    username: str
    password: str


class AppConfig(BaseModel):
    api: ApiConfig
    servers: list[ServerConfig]

    def get_server(self, server_code: str) -> Optional[ServerConfig]:
        for s in self.servers:
            if s.code == server_code:
                return s
        return None


def load_config() -> AppConfig:
    path = os.getenv('CONFIG_PATH', 'config.yaml')
    with open(path) as f:
        data = yaml.safe_load(f)
    return AppConfig.model_validate(data)
