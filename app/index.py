import os
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.helper import get_minecraft_status, wake_on_lan
from app.metrics import build_metrics
from app.command import execute_command


def load_env(name: str) -> str:
    env = os.getenv(name)
    if not env:
        raise RuntimeError(f"{name} is not set.")

    return env


HOST = load_env('HOST')
FRONTEND_ORIGIN = load_env("FRONTEND_ORIGIN")
WOL_TARGET_MAC_ADDRESS = load_env("WOL_TARGET_MAC_ADDRESS")
WOL_FROM_IP_ADDRESS = load_env("WOL_FROM_IP_ADDRESS")


app = FastAPI(
    title="Minecraft Server Monitor API",
    description="Forge / Vanilla 対応 Minecraft サーバー監視 API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)


class CommandRequest(BaseModel):
    code: str


@app.get("/health")
def health():
    return get_minecraft_status(host=HOST)


@app.post("/command")
def command(req: CommandRequest):
    return execute_command(req.code)


@app.post("/wake")
def wake():
    result = wake_on_lan(WOL_TARGET_MAC_ADDRESS, WOL_FROM_IP_ADDRESS)
    if result:
        return {
            'ok': True,
            'message': 'WOL Success'
        }
    else:
        return {
            'ok': False,
            'message': 'WOL Failed'
        }


@app.get("/metrics")
def metrics():
    status = get_minecraft_status(host=HOST)
    registry = build_metrics(status)

    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
