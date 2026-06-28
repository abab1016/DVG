#!/bin/bash
set -e

echo "=== Docker starten ==="
docker compose up -d

echo "=== Warte auf Zeebe (max 60s) ==="
for i in $(seq 1 30); do
  if curl -sf http://localhost:9600/actuator/health > /dev/null 2>&1; then
    echo "Zeebe ist bereit."
    break
  fi
  echo "  Warte... ($i/30)"
  sleep 2
done

echo "=== Ressourcen deployen ==="
python deploy_alles.py

echo "=== Worker starten (neues Fenster) ==="
cmd.exe /c "start cmd /k python worker\src\worker.py"

echo ""
echo "=== FERTIG ==="
echo "Tasklist: http://localhost:8082  (demo/demo)"
echo "Operate:  http://localhost:8081  (demo/demo)"
