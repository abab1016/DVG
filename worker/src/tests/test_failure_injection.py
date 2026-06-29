"""Tests fuer die skriptgesteuerten BPMN-Komponentenausfaelle."""
import builtins
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import ANY, AsyncMock, patch

import pytest

from failure_injection import (
    COMPONENTS,
    SimulatedComponentFailure,
    component_failure_exception_handler,
    marker_path,
    raise_if_failure_enabled,
)
from handlers.ai_extraction_handler import handle_ai_extraction
from handlers.archive_handler import handle_archivieren
from handlers.grpc_handler import handle_grpc_speichern
from handlers.payment_handler import handle_zahlung_senden
from handlers.uipath_handler import handle_uipath_erp_erfassung

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _PROJECT_ROOT / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

import component_failure as failure_cli  # noqa: E402


class FakeJob:
    def __init__(self, retries: int):
        self.retries = retries


class FakeJobController:
    def __init__(self):
        self.failure_calls = []
        self.error_calls = []

    async def set_failure_status(self, **kwargs):
        self.failure_calls.append(kwargs)

    async def set_error_status(self, **kwargs):
        self.error_calls.append(kwargs)


def _activate_marker(tmp_path: Path, monkeypatch, component: str) -> None:
    monkeypatch.setenv("DVG_FAILURE_DIR", str(tmp_path))
    path = marker_path(component)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("test", encoding="utf-8")


def test_deaktivierter_marker_veraendert_handler_nicht(tmp_path, monkeypatch):
    monkeypatch.setenv("DVG_FAILURE_DIR", str(tmp_path))
    raise_if_failure_enabled("grpc")


@pytest.mark.parametrize("component", COMPONENTS)
def test_aktivierter_marker_wirft_komponentenfehler(
    tmp_path,
    monkeypatch,
    component,
):
    _activate_marker(tmp_path, monkeypatch, component)

    with pytest.raises(SimulatedComponentFailure) as info:
        raise_if_failure_enabled(component)

    assert info.value.component == component
    assert info.value.error_code == COMPONENTS[component].error_code


@pytest.mark.parametrize("component", ["grpc", "rabbitmq", "archive"])
@pytest.mark.asyncio
async def test_exception_handler_verwendet_zeebe_retry_vor_letztem_versuch(
    component,
):
    controller = FakeJobController()
    error = SimulatedComponentFailure(COMPONENTS[component])

    await component_failure_exception_handler(error, FakeJob(3), controller)

    assert controller.error_calls == []
    assert controller.failure_calls == [{
        "message": str(error),
        "retry_back_off_ms": 1_000,
    }]


@pytest.mark.parametrize("component", COMPONENTS)
@pytest.mark.asyncio
async def test_exception_handler_wirft_beim_letzten_versuch_bpmn_error(
    component,
):
    controller = FakeJobController()
    config = COMPONENTS[component]
    error = SimulatedComponentFailure(config)

    await component_failure_exception_handler(error, FakeJob(1), controller)

    assert controller.failure_calls == []
    assert controller.error_calls == [{
        "message": str(error),
        "error_code": config.error_code,
    }]


@pytest.mark.asyncio
async def test_exception_handler_delegiert_normale_fehler():
    controller = FakeJobController()
    error = RuntimeError("normaler technischer Fehler")

    with patch(
        "failure_injection.default_exception_handler",
        new_callable=AsyncMock,
    ) as default_handler:
        await component_failure_exception_handler(error, FakeJob(3), controller)

    default_handler.assert_awaited_once()
    assert default_handler.await_args.args == (error, ANY, controller)
    assert controller.failure_calls == []
    assert controller.error_calls == []


@pytest.mark.parametrize(
    ("component", "handler", "variables"),
    [
        ("ai", handle_ai_extraction, {"fileName": "rechnung.pdf"}),
        ("grpc", handle_grpc_speichern, {"invoiceId": "INV-FAIL-GRPC"}),
        ("erp", handle_uipath_erp_erfassung, {"invoiceId": "INV-FAIL-ERP"}),
        ("rabbitmq", handle_zahlung_senden, {"invoiceId": "INV-FAIL-RMQ"}),
        ("archive", handle_archivieren, {"invoiceId": "INV-FAIL-ARCHIVE"}),
    ],
)
@pytest.mark.asyncio
async def test_jeder_bpmn_handler_prueft_seinen_marker(
    tmp_path,
    monkeypatch,
    component,
    handler,
    variables,
):
    _activate_marker(tmp_path, monkeypatch, component)

    with pytest.raises(SimulatedComponentFailure) as info:
        await handler(**variables)

    assert info.value.component == component


@pytest.mark.parametrize("component", COMPONENTS)
def test_cli_fail_status_restore(tmp_path, monkeypatch, component, capsys):
    monkeypatch.setenv("DVG_FAILURE_DIR", str(tmp_path))

    assert failure_cli.main([component, "fail"]) == 0
    assert (tmp_path / component).is_file()
    assert failure_cli.main([component, "status"]) == 0
    assert "AUSFALL AKTIV" in capsys.readouterr().out

    assert failure_cli.main([component, "restore"]) == 0
    assert not (tmp_path / component).exists()


def test_cli_oeffnet_ohne_aktion_das_menue(tmp_path, monkeypatch):
    monkeypatch.setenv("DVG_FAILURE_DIR", str(tmp_path))
    monkeypatch.setattr(builtins, "input", lambda _prompt: "1")

    assert failure_cli.main(["ai"]) == 0
    assert (tmp_path / "ai").is_file()


def test_cli_lehnt_unbekannte_aktion_ab(tmp_path, monkeypatch):
    monkeypatch.setenv("DVG_FAILURE_DIR", str(tmp_path))

    assert failure_cli.main(["grpc", "kaputt"]) == 2
    assert not (tmp_path / "grpc").exists()


def test_einzelne_windows_und_mac_skripte_existieren():
    for component in COMPONENTS:
        bat = _SCRIPTS_DIR / f"{component}_failure.bat"
        shell = _SCRIPTS_DIR / f"{component}_failure.sh"

        assert bat.is_file()
        assert shell.is_file()
        assert f'set "COMPONENT={component}"' in bat.read_text(encoding="utf-8")
        assert (
            f'component_failure.py" {component} "$@"'
            in shell.read_text(encoding="utf-8")
        )


def test_bpmn_retry_und_boundary_vertrag_stimmt_mit_konfiguration_ueberein():
    bpmn_path = _PROJECT_ROOT / "BPMN" / "G7_Rechnungsfreigabe_with_AI.bpmn"
    root = ET.parse(bpmn_path).getroot()
    ns = {
        "bpmn": "http://www.omg.org/spec/BPMN/20100524/MODEL",
        "zeebe": "http://camunda.org/schema/zeebe/1.0",
    }

    errors = {
        item.attrib["id"]: item.attrib["errorCode"]
        for item in root.findall("bpmn:error", ns)
    }
    tasks_by_job_type = {}
    for task in root.findall(".//bpmn:serviceTask", ns):
        definition = task.find(
            "bpmn:extensionElements/zeebe:taskDefinition",
            ns,
        )
        if definition is not None:
            tasks_by_job_type[definition.attrib["type"]] = (
                task.attrib["id"],
                int(definition.attrib.get("retries", "3")),
            )

    boundary_codes = {}
    for boundary in root.findall(".//bpmn:boundaryEvent", ns):
        error_definition = boundary.find("bpmn:errorEventDefinition", ns)
        if error_definition is not None:
            boundary_codes[boundary.attrib["attachedToRef"]] = errors[
                error_definition.attrib["errorRef"]
            ]

    for config in COMPONENTS.values():
        task_id, retries = tasks_by_job_type[config.job_type]
        assert retries == config.configured_retries
        assert boundary_codes[task_id] == config.error_code
