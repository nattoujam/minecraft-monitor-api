import hashlib
import hmac
import json
import secrets
import subprocess
import time
import urllib.error
import urllib.request

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from app.config import AppConfig, ServerConfig, load_config
from app.helper import MinecraftStatus, get_minecraft_status
from app.metrics import build_metrics

config: AppConfig = load_config()

app = FastAPI(
    title='Minecraft Server Monitor API',
    description='Forge / Vanilla 対応 Minecraft サーバー監視 API',
    version='2.0.0',
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.api.frontend_origin],
    allow_credentials=True,
    allow_methods=['GET', 'POST'],
    allow_headers=['*'],
)


def verify_session(request: Request):
    session_id = request.cookies.get('session_id')
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Not authenticated')

    try:
        expires_at_str, signature = session_id.split(':')
        expires_at = float(expires_at_str)

        if time.time() > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Session expired')

        expected_signature = hmac.new(
            config.api.password.encode('utf-8'), expires_at_str.encode('utf-8'), hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session')

    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid session format')


def get_server_or_404(server_code: str) -> ServerConfig:
    server = config.get_server(server_code)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Server '{server_code}' not found")
    return server


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post('/api/login')
def login(creds: LoginRequest, response: Response):
    match_username = secrets.compare_digest(creds.username.encode('utf8'), config.api.username.encode('utf8'))
    match_password = secrets.compare_digest(creds.password.encode('utf8'), config.api.password.encode('utf8'))

    if not (match_username and match_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Incorrect username or password')

    expires_at = time.time() + (7 * 24 * 60 * 60)
    signature = hmac.new(
        config.api.password.encode('utf-8'), str(expires_at).encode('utf-8'), hashlib.sha256
    ).hexdigest()
    session_id = f'{expires_at}:{signature}'

    response.set_cookie(key='session_id', value=session_id, httponly=True, max_age=7 * 24 * 60 * 60, samesite='lax')
    return {'ok': True}


@app.post('/api/logout')
def logout(response: Response):
    response.delete_cookie('session_id')
    return {'ok': True}


@app.get('/api/check_auth', dependencies=[Depends(verify_session)])
def check_auth() -> str:
    return 'ok'


class ServerInfo(BaseModel):
    code: str
    name: str


@app.get('/api/server/list', dependencies=[Depends(verify_session)])
def list_servers() -> list[ServerInfo]:
    return [
        ServerInfo(code=s.code, name=s.name)
        for s in config.servers
    ]


@app.get('/api/server/{server_code}/health', dependencies=[Depends(verify_session)])
def health(server_code: str) -> MinecraftStatus:
    server = get_server_or_404(server_code)
    return get_minecraft_status(host=server.host, port=server.port)


class ServerCommandResponse(BaseModel):
    ok: bool
    message: str


def _run_command(command: str, label: str) -> ServerCommandResponse:
    try:
        subprocess.Popen(command, shell=True)
        print(f'[cmd] {label}: {command}')
        return ServerCommandResponse(ok=True, message='command launched')
    except Exception as e:
        print(f'[cmd] {label} failed: {e}')
        return ServerCommandResponse(ok=False, message=str(e))


@app.post('/api/server/{server_code}/start', dependencies=[Depends(verify_session)])
def start(server_code: str) -> ServerCommandResponse:
    server = get_server_or_404(server_code)
    return _run_command(server.start_command, f'{server_code}/start')


@app.post('/api/server/{server_code}/stop', dependencies=[Depends(verify_session)])
def stop(server_code: str) -> ServerCommandResponse:
    server = get_server_or_404(server_code)
    return _run_command(server.stop_command, f'{server_code}/stop')


class MockStateRequest(BaseModel):
    state: str


@app.post('/dev/mock/{server_code}/state')
def dev_mock_state(server_code: str, req: MockStateRequest):
    server = get_server_or_404(server_code)
    if not server.mock_ctrl_url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Mock not configured for this server')

    data = json.dumps({'state': req.state}).encode()
    print(f'[dev] POST /dev/mock/{server_code}/state body={req.model_dump()}')
    request = urllib.request.Request(
        f'{server.mock_ctrl_url}/state',
        data=data,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')
        print(f'[dev] mock responded {e.code}: {body}')
        raise HTTPException(status_code=e.code, detail=body)
    except Exception as e:
        print(f'[dev] mock request failed: {e}')
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@app.get('/metrics')
def metrics() -> Response:
    results = [(s.code, get_minecraft_status(host=s.host, port=s.port)) for s in config.servers]
    registry = build_metrics(results)
    return Response(generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
