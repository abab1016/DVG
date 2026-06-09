#!/bin/bash
# Startup script for DVG Invoice Approval System on macOS

# Kein 'set -e', da Docker-Compose bei bekannten
# Ghost-Containern Fehler liefert, obwohl alles startet.

# Get the directory of this script
HIER="$(cd "$(dirname "$0")" && pwd)"

# Fester Compose-Projektname (vermeidet Ghost-Container-Konflikte)
export COMPOSE_PROJECT_NAME=dvg-app

echo "==========================================="
echo "  DVG Invoice System - Startup Script (Mac)"
echo "==========================================="
echo ""

# 0. Sicherstellen, dass Docker Desktop läuft
if ! docker info > /dev/null 2>&1; then
  echo ">>> 0. Docker Desktop wird gestartet..."
  open -a Docker
  echo -n "   Warte auf Docker Daemon"
  for i in $(seq 1 60); do
    if docker info > /dev/null 2>&1; then
      echo ""
      echo "   [OK] Docker Desktop ist bereit."
      break
    fi
    echo -n "."
    sleep 2
  done
  if ! docker info > /dev/null 2>&1; then
    echo ""
    echo "   [FEHLER] Docker Desktop konnte nicht gestartet werden!"
    exit 1
  fi
  echo ""
fi

# 1. Start Docker
echo ">>> 1. Starte Docker-Compose-Infrastruktur..."
docker compose up -d 2>&1
if [ $? -ne 0 ]; then
  echo "   [WARNUNG] Erster Start hatte Fehler, versuche force-recreate..."
  docker compose up -d --force-recreate 2>&1 || true
fi
echo "   [OK] Docker-Container gestartet."

# 2. Wait for Zeebe Gateway
echo ""
echo ">>> 2. Warte auf Zeebe Gateway Gesundheitsschnittstelle..."
for i in $(seq 1 60); do
  if curl -sf http://localhost:9600/actuator/health > /dev/null 2>&1; then
    echo "   [OK] Zeebe ist bereit."
    break
  fi
  if [ "$i" -eq 60 ]; then
    echo "   [FEHLER] Zeebe ist nach 120s nicht erreichbar!"
    echo "   Prüfe: docker compose logs zeebe"
    exit 1
  fi
  echo "   Warte auf Zeebe... ($i/60)"
  sleep 2
done

# 3. Deploy BPMN and Forms
echo ""
echo ">>> 3. Stelle BPMN-Prozess und Formulare bereit..."
python3 "$HIER/deploy_bmpn.py"
if [ $? -ne 0 ]; then
  echo "   [FEHLER] BPMN-Deployment fehlgeschlagen!"
  exit 1
fi

# 4. Start services in new Terminal windows
echo ""
echo ">>> 4. Starte Backend-Dienste in neuen Terminal-Fenstern..."

echo "   -> Starte gRPC Server..."
osascript -e "tell app \"Terminal\" to do script \"cd '$HIER' && echo '=== gRPC-Server ===' && python3 grpc-service/src/server.py\""

echo "   -> Starte Worker..."
osascript -e "tell app \"Terminal\" to do script \"cd '$HIER' && echo '=== Worker ===' && python3 worker/src/worker.py\""

echo "   -> Starte RabbitMQ Consumer..."
osascript -e "tell app \"Terminal\" to do script \"cd '$HIER' && echo '=== RabbitMQ Consumer ===' && python3 zahlungssystem/src/consumer.py\""

echo ""
echo "==========================================================="
echo "  [ERFOLG] Alle Systemkomponenten wurden gestartet!"
echo "==========================================================="
echo "  - Tasklist: http://localhost:8082  (Login: demo / demo)"
echo "  - Operate:  http://localhost:8081  (Login: demo / demo)"
echo ""
echo "  Du kannst jetzt eine neue E-Mail-Rechnung simulieren mit:"
echo "  -> python3 auto_email_start.py"
echo "==========================================================="
echo ""
