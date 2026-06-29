"""Laufzeitsteuerung fuer reproduzierbare BPMN-Komponentenausfaelle.

Die Demo-Skripte legen Markerdateien unter ``.dvg-runtime/failures`` an.
Handler pruefen diese Marker unmittelbar vor dem technischen Aufruf. Der
zentrale Exception-Handler nutzt die im BPMN konfigurierten Zeebe-Retries und
wirft beim letzten Versuch den passenden BPMN-Error fuer den Boundary-Pfad.
"""
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

from pyzeebe import default_exception_handler

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_FAILURE_DIR = _PROJECT_ROOT / ".dvg-runtime" / "failures"
_RETRY_BACK_OFF_MS = 1_000


@dataclass(frozen=True)
class ComponentConfig:
    key: str
    label: str
    job_type: str
    error_code: str
    configured_retries: int
    fallback: str


COMPONENTS: Dict[str, ComponentConfig] = {
    "ai": ComponentConfig(
        key="ai",
        label="AI / n8n",
        job_type="run-ai-extraction",
        error_code="ERR_AI_EXTRACTION",
        configured_retries=1,
        fallback="Metadaten manuell erfassen",
    ),
    "grpc": ComponentConfig(
        key="grpc",
        label="gRPC-Metadatenspeicherung",
        job_type="save-invoice-metadata",
        error_code="ERR_GRPC",
        configured_retries=3,
        fallback="Metadaten manuell speichern",
    ),
    "erp": ComponentConfig(
        key="erp",
        label="UiPath / ERP",
        job_type="uipath-erp-erfassung",
        error_code="ERR_UIPATH_FAILED",
        configured_retries=1,
        fallback="Rechnung manuell im ERP erfassen",
    ),
    "rabbitmq": ComponentConfig(
        key="rabbitmq",
        label="RabbitMQ-Zahlung",
        job_type="send-payment-order",
        error_code="ERR_RABBITMQ",
        configured_retries=3,
        fallback="Zahlung manuell erfassen",
    ),
    "archive": ComponentConfig(
        key="archive",
        label="Archivierung",
        job_type="archive-invoice",
        error_code="ERR_ARCHIVE",
        configured_retries=3,
        fallback="Rechnung manuell archivieren",
    ),
}


class SimulatedComponentFailure(RuntimeError):
    """Technischer Demo-Ausfall mit BPMN-Zielinformationen."""

    def __init__(self, config: ComponentConfig):
        self.component = config.key
        self.component_label = config.label
        self.error_code = config.error_code
        self.configured_retries = config.configured_retries
        self.fallback = config.fallback
        super().__init__(
            f"Simulierter Ausfall: {config.label}. "
            f"Nach den Retries folgt: {config.fallback}."
        )


def failure_directory() -> Path:
    """Liefert das dynamisch konfigurierbare Marker-Verzeichnis."""
    configured = os.getenv("DVG_FAILURE_DIR")
    return Path(configured) if configured else _DEFAULT_FAILURE_DIR


def marker_path(component: str) -> Path:
    """Liefert den Markerpfad oder meldet einen unbekannten Komponenten-Key."""
    if component not in COMPONENTS:
        raise ValueError(f"Unbekannte Ausfallkomponente: {component}")
    return failure_directory() / component


def raise_if_failure_enabled(component: str) -> None:
    """Wirft den steuerbaren technischen Fehler, wenn der Marker aktiv ist."""
    config = COMPONENTS.get(component)
    if config is None:
        raise ValueError(f"Unbekannte Ausfallkomponente: {component}")
    if marker_path(component).is_file():
        raise SimulatedComponentFailure(config)


async def component_failure_exception_handler(
    exception,
    job,
    job_controller,
) -> None:
    """Fuehrt simulierte Ausfaelle ueber Retry in den BPMN-Boundary-Error.

    Alle anderen Exceptions werden unveraendert an pyzeebes Standardbehandlung
    delegiert. Damit beeinflusst die Demo-Schaltung die bestehende
    Fehlerklassifizierung nicht.
    """
    if not isinstance(exception, SimulatedComponentFailure):
        await default_exception_handler(exception, job, job_controller)
        return

    retries_left = int(job.retries)
    attempt = max(1, exception.configured_retries - retries_left + 1)

    if retries_left > 1:
        logger.warning(
            "[Ausfallsimulation] %s: Versuch %d/%d fehlgeschlagen; "
            "Zeebe wiederholt den Job.",
            exception.component_label,
            attempt,
            exception.configured_retries,
        )
        await job_controller.set_failure_status(
            message=str(exception),
            retry_back_off_ms=_RETRY_BACK_OFF_MS,
        )
        return

    logger.error(
        "[Ausfallsimulation] %s: letzter Versuch fehlgeschlagen; "
        "BPMN-Error %s -> %s.",
        exception.component_label,
        exception.error_code,
        exception.fallback,
    )
    await job_controller.set_error_status(
        message=str(exception),
        error_code=exception.error_code,
    )
