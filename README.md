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
  "latency_ms": 15
}
```

```json
{
  "state": "stopped"
}
```

```json
{
  "state": "starting"
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
