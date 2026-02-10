import socket

from mcstatus import JavaServer
from netaddr import EUI, AddrFormatError, IPAddress
from pydantic import BaseModel
from wakeonlan import send_magic_packet


class MinecraftStatus(BaseModel):
    state: str
    online: int | None = None
    max: int | None = None
    motd: str | None = None
    version: str | None = None
    latency_ms: float | None = None
    icon: str | None = None


def get_minecraft_status(host: str = "localhost", port: int = 25565) -> MinecraftStatus:
    try:
        server = JavaServer(host, port, timeout=2)
        status = server.status()

        return MinecraftStatus(
            state="running",
            online=status.players.online,
            max=status.players.max,
            motd=str(status.motd.parsed[0]),
            version=status.version.name,
            latency_ms=status.latency,
            icon=status.icon
        )

    except socket.timeout:
        return MinecraftStatus(state="stopped")
    except ConnectionRefusedError:
        return MinecraftStatus(state="starting")
    except Exception:
        return MinecraftStatus(state="unknown")


def wake_on_lan(mac_address: str, interface_ip: str) -> bool:
    try:
        mac = EUI(mac_address)
    except AddrFormatError as e:
        print(f"Invalid MAC Address: {mac_address}\n{e}")
        return False

    try:
        ip = IPAddress(interface_ip)
    except AddrFormatError as e:
        print(f"Invalid IP Address: {interface_ip}\n{e}")
        return False

    send_magic_packet(str(mac), interface=str(ip))
    print(f"Send WakeOnLan from {str(ip)}, Target MAC Address: {str(mac)}, ")
    return True
