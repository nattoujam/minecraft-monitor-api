from mcstatus import JavaServer
from wakeonlan import send_magic_packet
from netaddr import IPAddress, EUI, AddrFormatError
import socket


def get_minecraft_status(host="localhost", port=25565, timeout=2):
    try:
        server = JavaServer(host, port, timeout=timeout)
        status = server.status()

        return {
            "state": "running",
            "online": status.players.online,
            "max": status.players.max,
            "motd": status.motd.parsed[0],
            "version": status.version.name,
            "latency_ms": status.latency,
            "icon": status.icon,
        }

    except socket.timeout:
        return {"state": "stopped"}
    except ConnectionRefusedError:
        return {"state": "starting"}
    except Exception as e:
        return {"state": "unknown", "error": str(e)}


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
