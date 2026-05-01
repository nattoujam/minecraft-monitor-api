import socket

from mcstatus import JavaServer
from pydantic import BaseModel


class MinecraftStatus(BaseModel):
    state: str
    online: int | None = None
    max: int | None = None
    motd: str | None = None
    version: str | None = None
    latency_ms: float | None = None
    icon: str | None = None


def get_minecraft_status(host: str = 'localhost', port: int = 25565) -> MinecraftStatus:
    try:
        server = JavaServer(host, port, timeout=2)
        status = server.status()

        return MinecraftStatus(
            state='running',
            online=status.players.online,
            max=status.players.max,
            motd=str(status.motd.parsed[0]),
            version=status.version.name,
            latency_ms=status.latency,
            icon=status.icon
        )

    except socket.timeout:
        return MinecraftStatus(state='stopped')
    except ConnectionRefusedError:
        return MinecraftStatus(state='starting')
    except Exception:
        return MinecraftStatus(state='unknown')
