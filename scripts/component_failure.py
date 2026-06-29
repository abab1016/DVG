#!/usr/bin/env python3
"""Gemeinsame CLI-Logik fuer die einzelnen Ausfallskripte."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FAILURE_DIR = PROJECT_ROOT / ".dvg-runtime" / "failures"

COMPONENT_LABELS: Dict[str, str] = {
    "ai": "AI / n8n",
    "grpc": "gRPC-Metadatenspeicherung",
    "erp": "UiPath / ERP",
    "rabbitmq": "RabbitMQ-Zahlung",
    "archive": "Archivierung",
}

VALID_ACTIONS = {"fail", "restore", "status"}


def failure_directory() -> Path:
    configured = os.getenv("DVG_FAILURE_DIR")
    return Path(configured) if configured else DEFAULT_FAILURE_DIR


def marker_path(component: str) -> Path:
    return failure_directory() / component


def print_status(component: str) -> None:
    active = marker_path(component).is_file()
    state = "AUSFALL AKTIV" if active else "betriebsbereit"
    print(f"[STATUS] {COMPONENT_LABELS[component]}: {state}")


def activate_failure(component: str) -> None:
    marker = marker_path(component)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        datetime.now(timezone.utc).isoformat(),
        encoding="utf-8",
    )
    print(f"[OK] Ausfall fuer {COMPONENT_LABELS[component]} aktiviert.")
    print("[INFO] Der Worker erkennt die Aenderung ohne Neustart.")
    print_status(component)


def restore_component(component: str) -> None:
    marker = marker_path(component)
    if marker.exists():
        marker.unlink()
        print(f"[OK] {COMPONENT_LABELS[component]} wiederhergestellt.")
    else:
        print(f"[INFO] {COMPONENT_LABELS[component]} war bereits betriebsbereit.")
    print_status(component)


def interactive_action(component: str) -> str:
    print()
    print(f"=== Ausfallsteuerung: {COMPONENT_LABELS[component]} ===")
    print("1 - Ausfall aktivieren")
    print("2 - Komponente wiederherstellen")
    print("3 - Status anzeigen")
    print()
    selection = input("Auswahl [1-3]: ").strip()
    return {
        "1": "fail",
        "2": "restore",
        "3": "status",
    }.get(selection, "")


def print_usage(script_name: str) -> None:
    print(f"Verwendung: {script_name} [fail|restore|status]")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] not in COMPONENT_LABELS:
        print("[FEHLER] Interner Aufruf ohne gueltige Komponente.")
        return 2

    component = args[0]
    if len(args) > 2:
        print("[FEHLER] Zu viele Argumente.")
        print_usage(Path(sys.argv[0]).name)
        return 2

    if len(args) == 1:
        try:
            action = interactive_action(component)
        except (EOFError, KeyboardInterrupt):
            print("\n[ABBRUCH] Keine Auswahl getroffen.")
            return 1
    else:
        action = args[1].lower()

    if action not in VALID_ACTIONS:
        print(f"[FEHLER] Unbekannte Aktion: {action or '<leer>'}")
        print_usage(Path(sys.argv[0]).name)
        return 2

    if action == "fail":
        activate_failure(component)
    elif action == "restore":
        restore_component(component)
    else:
        print_status(component)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
