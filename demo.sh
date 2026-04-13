#!/usr/bin/env bash
# DVG Demo-Skript
# Startet RabbitMQ, gRPC-Service und Zahlungssystem, dann den Client.
# Strg+C beendet alle Hintergrundprozesse.

set -e

WURZELVERZEICHNIS="$(cd "$(dirname "$0")" && pwd)"
GRPC_PROTOKOLL="$WURZELVERZEICHNIS/grpc-dienst.log"
CONSUMER_PROTOKOLL="$WURZELVERZEICHNIS/zahlungssystem.log"

aufraeumen() {
    echo ""
    echo "[Demo] Beende Hintergrundprozesse ..."
    [ -n "$GRPC_PROZESS" ]     && kill "$GRPC_PROZESS"     2>/dev/null || true
    [ -n "$CONSUMER_PROZESS" ] && kill "$CONSUMER_PROZESS" 2>/dev/null || true
    echo "[Demo] Protokolle: $GRPC_PROTOKOLL und $CONSUMER_PROTOKOLL"
}
trap aufraeumen EXIT

echo "[Demo] DVG End-to-End Demo"
echo ""

# Voraussetzungen prüfen
if command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
else
    echo "[Demo] Python nicht gefunden."
    exit 1
fi
command -v docker >/dev/null 2>&1 || { echo "[Demo] Docker nicht gefunden."; exit 1; }

if [ ! -f "$WURZELVERZEICHNIS/grpc-service/src/invoice_pb2.py" ]; then
    echo "[Demo] Proto-Stubs fehlen, werden generiert ..."
    cd "$WURZELVERZEICHNIS/grpc-service/src"
    "$PYTHON_CMD" -m grpc_tools.protoc -I proto --python_out=. --grpc_python_out=. proto/invoice.proto
    cd "$WURZELVERZEICHNIS"
fi

# RabbitMQ starten
echo "[Demo] Starte RabbitMQ ..."
cd "$WURZELVERZEICHNIS"
docker compose up -d rabbitmq

echo "[Demo] Warte bis RabbitMQ bereit ist ..."
VERSUCHE=0
until docker compose exec -T rabbitmq rabbitmq-diagnostics ping >/dev/null 2>&1; do
    VERSUCHE=$((VERSUCHE + 1))
    if [ $VERSUCHE -ge 24 ]; then
        echo "[Demo] RabbitMQ startet nicht (Zeitüberschreitung nach 2 Minuten)."
        exit 1
    fi
    sleep 5
done
echo "[Demo] RabbitMQ läuft auf localhost:5672 (Verwaltung: http://localhost:15672)"

# gRPC-Service starten
echo "[Demo] Starte gRPC-Service ..."
cd "$WURZELVERZEICHNIS/grpc-service/src"
"$PYTHON_CMD" -u server.py > "$GRPC_PROTOKOLL" 2>&1 &
GRPC_PROZESS=$!
cd "$WURZELVERZEICHNIS"

sleep 2
if ! kill -0 "$GRPC_PROZESS" 2>/dev/null; then
    echo "[Demo] gRPC-Server sofort abgestürzt, siehe: $GRPC_PROTOKOLL"
    exit 1
fi
echo "[Demo] gRPC-Service läuft auf localhost:50051 (Prozess $GRPC_PROZESS)"

# Zahlungssystem starten
echo "[Demo] Starte Zahlungssystem ..."
cd "$WURZELVERZEICHNIS/zahlungssystem/scr"
"$PYTHON_CMD" -u consumer.py > "$CONSUMER_PROTOKOLL" 2>&1 &
CONSUMER_PROZESS=$!
cd "$WURZELVERZEICHNIS"

sleep 2
if ! kill -0 "$CONSUMER_PROZESS" 2>/dev/null; then
    echo "[Demo] Zahlungssystem sofort abgestürzt, siehe: $CONSUMER_PROTOKOLL"
    exit 1
fi
echo "[Demo] Zahlungssystem läuft (Prozess $CONSUMER_PROZESS)"

echo ""

# Client starten
cd "$WURZELVERZEICHNIS/client/scr"

if [[ "$*" == *"--demo"* ]]; then
    echo "[Demo] Starte Demo-Durchlauf (nicht-interaktiv) ..."
    "$PYTHON_CMD" client.py
else
    echo "[Demo] Starte interaktive Oberfläche ..."
    "$PYTHON_CMD" ui.py
fi

cd "$WURZELVERZEICHNIS"
