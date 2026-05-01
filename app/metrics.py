from prometheus_client import CollectorRegistry, Gauge

from app.helper import MinecraftStatus


def build_metrics(servers: list[tuple[str, MinecraftStatus]]) -> CollectorRegistry:
    registry = CollectorRegistry()

    up = Gauge(
        'minecraft_server_up',
        'Minecraft server is up',
        ['server', 'state'],
        registry=registry,
    )
    players = Gauge(
        'minecraft_player_online',
        'Online players',
        ['server'],
        registry=registry,
    )

    for server_id, status in servers:
        for s in ['running', 'stopped', 'starting', 'unknown']:
            up.labels(server=server_id, state=s).set(1 if s == status.state else 0)
        players.labels(server=server_id).set(status.online or 0)

    return registry
