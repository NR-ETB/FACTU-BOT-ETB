import io
import json
import time
import zipfile
from pathlib import Path

import httpx
import pytest
from conftest import upload

FIXTURES = Path(__file__).parents[1] / "fixtures"


@pytest.mark.parametrize("suffix", ["csv", "xlsx"])
def test_five_clients_without_external_services(client, monkeypatch, suffix):
    def network_forbidden(*args, **kwargs):
        raise AssertionError("No se permiten llamadas HTTP externas en fase 1.")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", network_forbidden)
    started = time.perf_counter()
    source = FIXTURES / f"cinco_clientes.{suffix}"
    imported = upload(client, source.read_bytes(), source.name)
    assert imported["valid"] == 5 and imported["invalid"] == 0
    generated = client.post(
        "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
    ).json()
    expected_totals = [
        "setenta mil pesos",
        "ciento cinco mil pesos",
        "noventa y cinco mil pesos",
        "ciento diecinueve mil pesos",
        "ciento quince mil pesos",
    ]
    for item, spoken_total in zip(generated["results"], expected_totals, strict=True):
        script = client.get("/api/v1/scripts/" + item["script_id"]).json()
        assert script["status"] == "VALIDADO"
        assert f"El total de tu factura es de {spoken_total}." in script["payload"]["text"]
        assert all(binding["verified"] for binding in script["payload"]["evidence"])
        invoice = client.get("/api/v1/invoices/" + item["invoice_id"]).json()
        lines = [s for s in script["payload"]["segments"] if s["kind"] == "line"]
        assert len(lines) == len(invoice["source"]["lines"])
        assert [s["amount"] for s in lines] == [s["amount"] for s in invoice["source"]["lines"]]
    response = client.get(f"/api/v1/imports/{imported['id']}/export")
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        report = json.loads(archive.read("informe.json"))
        assert len(report["scripts"]) == 5
    assert time.perf_counter() - started < 10
