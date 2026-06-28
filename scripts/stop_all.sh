#!/bin/bash
# Stop script for DVG Invoice Approval System on macOS

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# Muss zum start_all.sh Projektnamen passen
export COMPOSE_PROJECT_NAME=dvg-app

echo "==========================================="
echo "  DVG Invoice System - Stop Script (Mac)"
echo "==========================================="
echo ""

# 1. Stop Python services
echo ">>> 1. Stoppe Python-Dienste..."

STOPPED=0

if pgrep -f "worker.py" > /dev/null 2>&1; then
  pkill -f "worker.py"
  echo "   [✓] Worker gestoppt."
  STOPPED=$((STOPPED + 1))
else
  echo "   [-] Worker läuft nicht."
fi

if pgrep -f "grpc-service/src/server.py|grpc_server.py" > /dev/null 2>&1; then
  pkill -f "grpc-service/src/server.py|grpc_server.py"
  echo "   [✓] gRPC-Server gestoppt."
  STOPPED=$((STOPPED + 1))
else
  echo "   [-] gRPC-Server läuft nicht."
fi

if pgrep -f "zahlungssystem/src/consumer.py|rabbitmq_consumer.py" > /dev/null 2>&1; then
  pkill -f "zahlungssystem/src/consumer.py|rabbitmq_consumer.py"
  echo "   [✓] RabbitMQ Consumer gestoppt."
  STOPPED=$((STOPPED + 1))
else
  echo "   [-] RabbitMQ Consumer läuft nicht."
fi

if pgrep -f "auto_email_start.py" > /dev/null 2>&1; then
  pkill -f "auto_email_start.py"
  echo "   [✓] E-Mail-Starter gestoppt."
  STOPPED=$((STOPPED + 1))
else
  echo "   [-] E-Mail-Starter läuft nicht."
fi

echo ""
echo "   $STOPPED Python-Prozess(e) gestoppt."

# 2. Stop Docker containers
echo ""
echo ">>> 2. Stoppe Docker-Container..."
docker compose down --remove-orphans 2>&1 || true
echo "   [✓] Docker-Container gestoppt."

# 3. Free ports (safety check)
echo ""
echo ">>> 3. Prüfe Ports..."

for PORT in 8082 8081 26500 9600 8090; do
  PID=$(lsof -ti :$PORT 2>/dev/null)
  if [ -n "$PID" ]; then
    kill -9 $PID 2>/dev/null
    echo "   [✓] Port $PORT freigegeben (PID: $PID)."
  fi
done

echo ""
echo "==========================================="
echo "  [ERFOLG] Alles wurde gestoppt!"
echo "==========================================="
echo "  Zum Neustarten: ./scripts/start_all.sh"
echo "==========================================="
echo ""

# 4. Schließe die Terminal-Fenster, die von start_all.sh geöffnet wurden
echo ">>> 4. Räume Terminal-Fenster auf..."
osascript -e '
tell application "Terminal"
    set windowIdsToClose to {}
    repeat with w in windows
        try
            repeat with t in tabs of w
                set tabHistory to history of t
                if tabHistory contains "=== gRPC-Server ===" or tabHistory contains "=== Worker ===" or tabHistory contains "=== RabbitMQ Consumer ===" then
                    set end of windowIdsToClose to id of w
                    exit repeat
                end if
            end repeat
        end try
    end repeat
    repeat with wId in windowIdsToClose
        try
            close window id wId saving no
        end try
    end repeat
end tell
' >/dev/null 2>&1
echo "   [✓] Geöffnete Hintergrund-Terminals geschlossen."
echo ""
