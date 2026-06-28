#!/bin/bash
# Installation and setup script for DVG Invoice Approval System
# Supports macOS and Windows (Git Bash/WSL)

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================================="
echo "  DVG Invoice System - Installation & Setup"
echo "=========================================================="
echo ""

# 1. Plattform aus plattform.txt auslesen
PLATFORM="mac"
if [ -f plattform.txt ]; then
  PLATFORM=$(cat plattform.txt | tr -d '\r' | tr -d '\n' | tr '[:upper:]' '[:lower:]')
  echo "[INFO] Plattform aus plattform.txt erkannt: $PLATFORM"
else
  # Auto-detect fallback
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
    PLATFORM="windows"
  else
    PLATFORM="mac"
  fi
  echo "[INFO] plattform.txt nicht gefunden. Auto-Erkennung: $PLATFORM"
fi

# 2. Ordner strukturieren / vorbereiten
echo ""
echo ">>> [1/4] Bereite Arbeitsordner vor..."
mkdir -p Rechnungsdaten
echo "    -> Ordner 'Rechnungsdaten' erstellt/verifiziert."

# 3. Python suchen und Abhängigkeiten installieren
echo ""
echo ">>> [2/4] Überprüfe Python-Installation..."
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
  PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
  PYTHON_CMD="python"
elif command -v py &>/dev/null; then
  PYTHON_CMD="py"
else
  echo "    [FEHLER] Kein Python installiert! Bitte installiere Python 3."
  exit 1
fi

echo "    -> Verwende Python-Befehl: $PYTHON_CMD"
$PYTHON_CMD --version

echo ""
echo ">>> [3/4] Installiere Python-Abhängigkeiten..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r worker/requirements.txt
$PYTHON_CMD -m pip install -r grpc-service/requirements.txt
$PYTHON_CMD -m pip install -r zahlungssystem/requirements.txt

if [ $? -eq 0 ]; then
  echo "    [OK] Python-Abhängigkeiten erfolgreich installiert."
else
  echo "    [WARNUNG] Installation der Python-Abhängigkeiten fehlgeschlagen oder unvollständig."
  echo "              Bitte führe die Installation manuell aus."
fi

# 4. Docker-Images vorbereiten (optional, falls Docker läuft)
echo ""
echo ">>> [4/4] Bereite Docker-Infrastruktur vor..."
if command -v docker &>/dev/null && docker info >/dev/null 2>&1; then
  echo "    -> Docker-Daemon läuft. Lade Container-Images herunter..."
  docker compose pull
  echo "    [OK] Docker-Images heruntergeladen."
else
  echo "    [INFO] Docker läuft gerade nicht oder ist nicht installiert."
  echo "           Die Images werden beim ersten Aufruf von 'start_all.sh' geladen."
fi

echo ""
echo "=========================================================="
echo "  [ERFOLG] Installation und Setup abgeschlossen!"
echo "=========================================================="
echo "  Die Plattform wurde auf '$PLATFORM' konfiguriert."
echo "  Du kannst das System nun starten mit:"
echo "  -> ./scripts/start_all.sh"
echo "=========================================================="
echo ""
