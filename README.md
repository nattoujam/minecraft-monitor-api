# Minecraft Monitor API

複数の Minecraft サーバーを監視・管理する REST API です。

## 設定

`config.yaml` を作成してサーバー情報を定義します。

```yaml
api:
  frontend_origin: http://localhost:5173
  username: admin
  password: CHANGE_ME

servers:
  - code: survival
    name: サバイバル
    host: 192.168.10.11
    port: 25565
    start_command: 'systemctl start minecraft-survival'
    stop_command: 'systemctl stop minecraft-survival'
```

| フィールド | 必須 | 説明 |
|---|---|---|
| `code` | ✓ | サーバーの識別子（URLパスに使用） |
| `name` | ✓ | 表示名 |
| `host` | ✓ | Minecraft サーバーのホスト |
| `port` | ✓ | Minecraft サーバーのポート（デフォルト: 25565） |
| `start_command` | ✓ | 起動時に実行するコマンド |
| `stop_command` | ✓ | 停止時に実行するコマンド |

## ローカル起動

### 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 本番サーバーに向けて起動

`config.yaml` を編集して実際のサーバー情報を設定した上で起動します。

```bash
./start.sh
```

### Mock サーバーを使って起動（検証環境）

Mock サーバーを使うことで、実際の Minecraft サーバーなしに動作確認できます。
`config.yaml` の `start_command` / `stop_command` に `mock/start_bg.sh` / `mock/stop_bg.sh` を指定することで、API 経由で Mock サーバーの起動・停止を制御できます。

```yaml
servers:
  - code: survival
    name: サバイバル
    host: localhost
    port: 25565
    start_command: 'bash mock/start_bg.sh survival 25565 8080'
    stop_command: 'bash mock/stop_bg.sh survival'
    mock_ctrl_url: http://localhost:8080
```

| フィールド | 説明 |
|---|---|
| `start_command` | `mock/start_bg.sh <code> <mc_port> <ctrl_port>` を指定する |
| `stop_command` | `mock/stop_bg.sh <code>` を指定する |
| `mock_ctrl_url` | Mock の状態切り替え（`/dev/mock/{code}/state`）に使用する制御 API の URL |

上記の設定で `./start.sh` を起動すると、`/api/server/{code}/start` で Mock サーバーが立ち上がります。

## Docker で起動

`config.yaml` をマウントして起動します。

```bash
docker compose up -d
```

## API エンドポイント

認証が必要なエンドポイントは事前に `/api/login` でセッションを取得してください。

### 認証

| Method | Path | 説明 |
|---|---|---|
| POST | `/api/login` | ログイン |
| POST | `/api/logout` | ログアウト |
| GET | `/api/check_auth` | 認証確認 |

### サーバー管理

| Method | Path | 認証 | 説明 |
|---|---|---|---|
| GET | `/api/server/list` | ✓ | サーバー一覧取得 |
| GET | `/api/server/{code}/health` | ✓ | サーバー状態取得 |
| POST | `/api/server/{code}/start` | ✓ | サーバー起動 |
| POST | `/api/server/{code}/stop` | ✓ | サーバー停止 |

### メトリクス

| Method | Path | 説明 |
|---|---|---|
| GET | `/metrics` | Prometheus メトリクス（全サーバー） |

### レスポンス例

`GET /api/server/list`

```json
[
  {
    "code": "survival",
    "name": "サバイバル"
  },
  {
    "code": "creative",
    "name": "クリエイティブ"
  }
]
```

`GET /api/server/{code}/health`

```json
{
  "state": "running",
  "online": 3,
  "max": 20,
  "motd": "Survival Server",
  "version": "1.20.1",
  "latency_ms": 12.5,
  "icon": null
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

state は `running` / `stopped` / `starting` / `unknown` のいずれかです。
