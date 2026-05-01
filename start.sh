#!/bin/bash

export CONFIG_PATH="config.yaml"

uvicorn app.index:app --host 0.0.0.0 --port 8000 --reload
