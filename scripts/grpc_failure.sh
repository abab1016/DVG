#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_CMD="python"
else
  echo "[FEHLER] Kein Python 3 gefunden."
  exit 1
fi

exec "$PYTHON_CMD" "$SCRIPT_DIR/component_failure.py" grpc "$@"
