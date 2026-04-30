import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.error
import urllib.request

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from pydantic import BaseModel

from app.helper import MinecraftStatus, get_minecraft_status, wake_on_lan
from app.metrics import build_metrics


def load_env(name: str) -> str:
    env = os.getenv(name)
    if not env:
        raise RuntimeError(f"{name} is not set.")

    return env


HOST = load_env('HOST')
PORT = int(load_env('PORT'))
FRONTEND_ORIGIN = load_env("FRONTEND_ORIGIN")
WOL_TARGET_MAC_ADDRESS = load_env("WOL_TARGET_MAC_ADDRESS")
WOL_FROM_IP_ADDRESS = load_env("WOL_FROM_IP_ADDRESS")
API_USERNAME = load_env("API_USERNAME")
API_PASSWORD = load_env("API_PASSWORD")

# Dev only: set to mock server control URL (e.g. http://localhost:8080)
MOCK_CTRL_URL = os.getenv("MOCK_CTRL_URL")


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


def verify_session(request: Request):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        expires_at_str, signature = session_id.split(":")
        expires_at = float(expires_at_str)

        if time.time() > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

        expected_signature = hmac.new(
            API_PASSWORD.encode("utf-8"), expires_at_str.encode("utf-8"), hashlib.sha256
        ).hexdigest()

        if not secrets.compare_digest(signature, expected_signature):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session format")


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/api/login")
def login(creds: LoginRequest, response: Response):
    match_username = secrets.compare_digest(creds.username.encode("utf8"), API_USERNAME.encode("utf8"))
    match_password = secrets.compare_digest(creds.password.encode("utf8"), API_PASSWORD.encode("utf8"))

    if not (match_username and match_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    expires_at = time.time() + (7 * 24 * 60 * 60)  # 7 days
    signature = hmac.new(
        API_PASSWORD.encode("utf-8"), str(expires_at).encode("utf-8"), hashlib.sha256
    ).hexdigest()
    session_id = f"{expires_at}:{signature}"

    response.set_cookie(key="session_id", value=session_id, httponly=True, max_age=7 * 24 * 60 * 60, samesite="lax")
    return {"ok": True}


@app.post("/api/logout")
def logout(response: Response):
    response.delete_cookie("session_id")
    return {"ok": True}


@app.get("/api/check_auth", dependencies=[Depends(verify_session)])
def check_auth() -> str:
    return 'ok'


@app.get("/api/health", dependencies=[Depends(verify_session)])
def health() -> MinecraftStatus:
    return get_minecraft_status(host=HOST, port=PORT)


class WakeOnLanResponse(BaseModel):
    ok: bool
    message: str


@app.post("/api/wake", dependencies=[Depends(verify_session)])
def wake() -> WakeOnLanResponse:
    result = wake_on_lan(WOL_TARGET_MAC_ADDRESS, WOL_FROM_IP_ADDRESS)
    if result:
        return WakeOnLanResponse(ok=True, message='WOL Success')
    else:
        return WakeOnLanResponse(ok=False, message='WOL Failed')


class MockStateRequest(BaseModel):
    state: str


@app.post("/dev/mock/state")
def dev_mock_state(req: MockStateRequest):
    if not MOCK_CTRL_URL:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    data = json.dumps({"state": req.state}).encode()
    print(f"[dev] POST /dev/mock/state body={req.model_dump()}")
    request = urllib.request.Request(
        f"{MOCK_CTRL_URL}/state",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        print(f"[dev] mock responded {e.code}: {body}")
        raise HTTPException(status_code=e.code, detail=body)
    except Exception as e:
        print(f"[dev] mock request failed: {e}")
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@app.get("/metrics")
def metrics() -> Response:
    status = get_minecraft_status(host=HOST, port=PORT)
    registry = build_metrics(status)

    return Response(
        generate_latest(registry),
        media_type=CONTENT_TYPE_LATEST,
    )
