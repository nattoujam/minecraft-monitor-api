from prometheus_client import (
    Gauge,
    CollectorRegistry,
)

registry = CollectorRegistry()


def build_metrics(status):
    registry = CollectorRegistry()

    up = Gauge(
        "minecraft_server_up",
        "Minecraft server is up",
        ["state"],
        registry=registry
    )
    for s in ["running", "stopping", "starting", "unknown"]:
        up.labels(state=s).set(1 if s == status['state'] else 0)

    players = Gauge(
        "minecraft_player_online",
        "Online players",
        registry=registry
    )
    players.set(status['online'])

    return registry
