FROM python:3.11-slim

WORKDIR /app

# コンテナの起動・停止を制御できるようDocker CLIをインストール
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.index:app", "--host", "0.0.0.0", "--port", "8000"]
