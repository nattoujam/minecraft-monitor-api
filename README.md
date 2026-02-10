# Minecraft-Monitor-API
## Usage

create container

```bash
docker compose up -d
```

## test request
### get status

```bash
curl http://localhost:8000/health
```

response

```json
{
  "state": "running",
  "online": 2,
  "max": 20,
  "motd": "Forge Survival Server",
  "version": "1.20.1",
  "latency_ms": 15,
  "icon": "<bolb text>"
}
```

```json
{
  "state": "stopped",
  "online": null,
  "max": null,
  "motd": null,
  "version": null,
  "latency_ms": null,
  "icon": null
}
```

```json
{
  "state": "starting",
  "online": null,
  "max": null,
  "motd": null,
  "version": null,
  "latency_ms": null,
  "icon": null
}
```

### post WOL

```bash
curl -X POST http://localhost:8000/wake
```

response

```json
{
  "ok": true,
  "message": "WOL Success"
}
```

```json
{
  "ok": false,
  "message": "WOL Failed"
}
```
