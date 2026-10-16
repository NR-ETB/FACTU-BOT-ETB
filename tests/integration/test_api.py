import io
import json
import zipfile
from pathlib import Path

import pytest
from conftest import upload
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from videofacturacion.api.main import create_app
from videofacturacion.application.service import BillingService, ServiceError
from videofacturacion.config import Settings
from videofacturacion.persistence.models import LineRecord, ScriptRecord

FIXTURES = Path(__file__).parents[1] / "fixtures"


def test_full_lifecycle_persist_review_export_delete(client, sample):
    imported = upload(client, sample)
    assert imported["valid"] == 5 and imported["invalid"] == 0
    assert upload(client, sample)["id"] == imported["id"]
    assert len(client.get("/api/v1/imports").json()) == 1
    invoices = client.get("/api/v1/invoices", params={"import_id": imported["id"]}).json()
    assert [i["total"] for i in invoices] == [
        "70000.00",
        "105000.00",
        "95000.00",
        "119000.00",
        "115000.00",
    ]
    generated = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
    ).json()["results"]
    assert len(generated) == 5 and all("script_id" in g for g in generated)
    repeated = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
    ).json()["results"]
    assert all(item["reused"] for item in repeated)
    script_id = generated[0]["script_id"]
    script = client.get("/api/v1/scripts/" + script_id).json()
    assert script["status"] == "VALIDADO"
    assert (
        client.post(
            f"/api/v1/scripts/{script_id}/reviews", json={"decision": "RECHAZADO"}
        ).status_code
        == 422
    )
    reviewed = client.post(
        f"/api/v1/scripts/{script_id}/reviews", json={"decision": "APROBADO"}
    ).json()
    assert reviewed["status"] == "APROBADO" and len(reviewed["reviews"]) == 1
    client.post(
        f"/api/v1/scripts/{script_id}/reviews",
        json={"decision": "RECHAZADO", "reason": "Revisar redacción"},
    )
    assert client.get("/api/v1/scripts/" + script_id).json()["status"] == "RECHAZADO"
    export = client.get(f"/api/v1/imports/{imported['id']}/export")
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        report = json.loads(archive.read("informe.json"))
        assert len(report["scripts"]) == 5
        assert len([n for n in archive.namelist() if n.endswith(".txt")]) == 5
    with client.app.state.service.sessions() as session:
        line = session.scalar(select(LineRecord))
        assert isinstance(line.amount_cents, int) and line.amount_cents == 7000000
    data_dir = client.app.state.service.settings.data_dir
    assert len(list((data_dir / "sources").iterdir())) == 1
    assert client.delete(f"/api/v1/imports/{imported['id']}").status_code == 204
    assert client.get("/api/v1/scripts/" + script_id).status_code == 404
    assert list((data_dir / "sources").iterdir()) == []


def test_xlsx_csv_equivalence(client, sample):
    imported_csv = upload(client, sample)
    csv_invoices = client.get("/api/v1/invoices", params={"import_id": imported_csv["id"]}).json()
    imported_xlsx = upload(client, (FIXTURES / "cinco_clientes.xlsx").read_bytes(), "test.xlsx")
    xlsx_invoices = client.get("/api/v1/invoices", params={"import_id": imported_xlsx["id"]}).json()
    assert [i["source"]["header"] for i in csv_invoices] == [
        i["source"]["header"] for i in xlsx_invoices
    ]
    assert all(i["status"] == "VALIDA" for i in xlsx_invoices)


def test_partial_validation_and_structural_audit(client, sample):
    altered = sample.replace(b";70000.00\n", b";70000.01\n", 1)
    imported = upload(client, altered)
    assert imported["invalid"] == 1 and imported["valid"] == 4
    results = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
    ).json()["results"]
    assert results[0]["error"]["code"] == "INVOICE_BLOCKED"
    bad = upload(client, b"not;a;valid;file\nfoo;bar\n")
    assert bad["status"] == "RECHAZADO" and bad["invoice_ids"] == []
    assert bad["issues"][0]["code"] == "INVALID_COLUMNS"


def test_source_and_template_changes_block_previous_approval(client, sample):
    imported = upload(client, sample)
    result = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": [imported["invoice_ids"][0]]}
    ).json()
    script_id = result["results"][0]["script_id"]
    client.post(f"/api/v1/scripts/{script_id}/reviews", json={"decision": "APROBADO"})
    altered = sample.replace(b"70000.00", b"70001.00")
    upload(client, altered)
    assert client.get("/api/v1/scripts/" + script_id).json()["status"] == "OBSOLETO"
    assert (
        client.post(
            f"/api/v1/scripts/{script_id}/reviews", json={"decision": "APROBADO"}
        ).status_code
        == 409
    )
    imported_new = upload(client, altered)
    result = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": [imported_new["invoice_ids"][0]]}
    ).json()
    new_id = result["results"][0]["script_id"]
    client.app.state.service.scripts.template_hash = "new-template"
    assert client.get("/api/v1/scripts/" + new_id).json()["status"] == "OBSOLETO"


def test_saved_corrupt_script_cannot_be_approved(client, sample):
    imported = upload(client, sample)
    result = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": [imported["invoice_ids"][0]]}
    ).json()
    script_id = result["results"][0]["script_id"]
    with client.app.state.service.sessions.begin() as session:
        script = session.get(ScriptRecord, script_id)
        script.payload = dict(script.payload, text="Un valor inventado.")
    assert client.get("/api/v1/scripts/" + script_id).json()["status"] == "BLOQUEADO"
    assert (
        client.post(
            f"/api/v1/scripts/{script_id}/reviews", json={"decision": "APROBADO"}
        ).status_code
        == 409
    )


def test_restart_and_migration_are_idempotent(tmp_path, sample):
    settings = Settings(data_dir=tmp_path / "persisted")
    with TestClient(create_app(settings)) as first:
        imported = upload(first, sample)
        result = first.post(
            "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
        ).json()
        script_id = result["results"][0]["script_id"]
        first.post(f"/api/v1/scripts/{script_id}/reviews", json={"decision": "APROBADO"})
    with TestClient(create_app(settings)) as second:
        assert second.get(f"/api/v1/scripts/{script_id}").json()["status"] == "APROBADO"
        assert second.get(f"/api/v1/imports/{imported['id']}").json()["valid"] == 5


def test_etb_profile_checks_subtotal_and_total(client):
    sample = (FIXTURES / "etb_prueba_sintetica.csv").read_bytes()
    imported = upload(client, sample, profile="etb_prueba_v1")
    assert imported["valid"] == 1
    result = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
    ).json()
    script = client.get("/api/v1/scripts/" + result["results"][0]["script_id"]).json()
    assert "ciento treinta mil pesos" in script["payload"]["text"]
    assert "un descuento de diez mil pesos" in script["payload"]["text"]
    discount = next(e for e in script["payload"]["evidence"] if e.get("line_id") == "descuento")
    assert discount["source"]["raw"] == "10000" and discount["normalized"] == "-10000.00"
    bad = upload(client, sample.replace(b",140000,", b",140001,"), profile="etb_prueba_v1")
    invoice = client.get("/api/v1/invoices/" + bad["invoice_ids"][0]).json()
    assert "SUBTOTAL_MISMATCH" in {i["code"] for i in invoice["issues"]}


def test_synthetic_confirmation_and_safe_errors(client, sample):
    response = client.post("/api/v1/imports", files={"file": ("test.csv", sample)})
    assert response.status_code == 422 and response.json()["error"]["code"] == "SYNTHETIC_ONLY"
    response = client.post("/api/v1/scripts/batch", json={"invoice_ids": "private-input"})
    assert response.status_code == 422 and "private-input" not in response.text
    assert client.get("/api/v1/health").json()["audiovisual_enabled"] is False
    assert client.post("/api/v1/video-jobs/batch", json={}).status_code == 404


def test_delete_restores_source_if_database_operation_fails(client, sample, monkeypatch):
    imported = upload(client, sample)
    service = client.app.state.service
    original_execute = Session.execute

    def failed_delete(session, statement, *args, **kwargs):
        if getattr(statement, "is_delete", False):
            raise OSError("simulated database failure")
        return original_execute(session, statement, *args, **kwargs)

    with monkeypatch.context() as context:
        context.setattr(Session, "execute", failed_delete)
        with pytest.raises(OSError):
            service.delete_import(imported["id"])
    assert service.get_import(imported["id"])["valid"] == 5
    assert (service.sources / imported["filename"]).read_bytes() == sample
    assert not list(service.sources.glob("*.deleted"))


def test_pending_file_deletion_is_completed_on_restart(client, sample, monkeypatch):
    imported = upload(client, sample)
    service = client.app.state.service

    def disk_failure(path):
        raise OSError("simulated file lock")

    monkeypatch.setattr(service.storage, "finish_delete", disk_failure)
    with pytest.raises(ServiceError) as error:
        service.delete_import(imported["id"])
    assert error.value.code == "DELETION_CLEANUP_PENDING"
    assert list(service.sources.glob("*.deleted"))
    restarted = BillingService(service.settings)
    try:
        assert restarted.list_imports() == []
        assert list(restarted.sources.iterdir()) == []
    finally:
        restarted.engine.dispose()
