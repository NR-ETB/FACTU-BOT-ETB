from copy import deepcopy

import pytest

from videofacturacion.config import Settings
from videofacturacion.ingestion.reader import parse_file
from videofacturacion.scripts.engine import ScriptEngine


@pytest.fixture
def generated(sample):
    invoice = parse_file(sample, "test.csv", "conceptos_v1", Settings()).invoices[2]
    engine = ScriptEngine()
    return invoice, engine, engine.generate(invoice)


def test_discount_golden(generated):
    invoice, engine, script = generated
    assert "un descuento de cinco mil pesos" in script["text"]
    assert "El total de tu factura es de noventa y cinco mil pesos." in script["text"]
    assert "veinticinco de octubre de dos mil veintiséis" in script["text"]
    assert engine.verify(invoice, script) == []
    assert engine.generate(invoice) == script


@pytest.mark.parametrize(
    "mutation",
    ["amount", "missing", "duplicate", "client", "date", "text", "evidence", "sense", "source"],
)
def test_detects_script_corruption(generated, mutation):
    invoice, engine, script = generated
    altered = deepcopy(script)
    if mutation == "amount":
        altered["segments"][1]["amount"] = "999.00"
    elif mutation == "missing":
        altered["segments"].pop(1)
    elif mutation == "duplicate":
        altered["segments"].insert(1, deepcopy(altered["segments"][1]))
    elif mutation == "client":
        altered["segments"][0]["text"] = "Hola, otro cliente."
    elif mutation == "date":
        altered["segments"][-1]["text"] = "Vence mañana."
    elif mutation == "text":
        altered["text"] += " Cargo adicional de cien pesos."
    elif mutation == "evidence":
        altered["evidence"][0]["normalized"] = "0.00"
    elif mutation == "sense":
        altered["segments"][2]["text"] = altered["segments"][2]["text"].replace(
            "un descuento", "un cargo"
        )
    elif mutation == "source":
        altered["segments"][1]["source"]["row"] = 999
    assert engine.verify(invoice, altered)


def test_changed_template_invalidates(generated):
    invoice, engine, script = generated
    engine.template_hash = "new-version"
    assert "STALE_TEMPLATE" in engine.verify(invoice, script)
