#!/bin/bash
# Stop script for DVG Invoice Approval System on macOS

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

if pgrep -f "grpc_server.py\|server.py.*grpc" > /dev/null 2>&1; then
  pkill -f "grpc_server.py\|server.py.*grpc"
  echo "   [✓] gRPC-Server gestoppt."
  STOPPED=$((STOPPED + 1))
else
  echo "   [-] gRPC-Server läuft nicht."
fi

if pgrep -f "rabbitmq_consumer.py\|consumer.py.*zahlungssystem" > /dev/null 2>&1; then
  pkill -f "rabbitmq_consumer.py\|consumer.py.*zahlungssystem"
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
echo "  Zum Neustarten: ./start_all.sh"
echo "==========================================="
echo ""
