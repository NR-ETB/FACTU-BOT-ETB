from decimal import Decimal

import pytest
from PIL import Image

from videofacturacion.audiovisual.cards import display_money, render_card, scene_data
from videofacturacion.config import Settings
from videofacturacion.ingestion.reader import parse_file
from videofacturacion.scripts.engine import ScriptEngine


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        ("130000.00", "$ 130.000 COP"),
        ("-10000.00", "−$ 10.000 COP"),
        ("0.01", "$ 0,01 COP"),
        ("1.50", "$ 1,50 COP"),
    ],
)
def test_visual_money_exact(amount, expected):
    assert display_money(amount) == expected


def test_visual_scene_rejects_changed_amount(sample):
    invoice = parse_file(sample, "test.csv", "conceptos_v1", Settings()).invoices[0]
    script = ScriptEngine().generate(invoice)
    segment = dict(script["segments"][1], amount="70000.01")
    with pytest.raises(ValueError):
        scene_data(invoice, segment)


def test_renders_every_line_and_total_without_changing_source(sample, tmp_path):
    invoice = parse_file(sample, "test.csv", "conceptos_v1", Settings()).invoices[2]
    script = ScriptEngine().generate(invoice)
    for index, segment in enumerate(script["segments"]):
        target = tmp_path / f"{index}.png"
        visual = render_card(invoice, segment, index, len(script["segments"]), target)
        with Image.open(target) as image:
            assert image.size == (1280, 720)
        if segment["kind"] == "line" and Decimal(segment["amount"]) < 0:
            assert visual["value"] == "−$ 5.000 COP"
    assert ScriptEngine().verify(invoice, script) == []
