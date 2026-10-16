import csv
import io
from decimal import Decimal

import pytest
from openpyxl import Workbook

from videofacturacion.config import Settings
from videofacturacion.ingestion.reader import InputError, parse_file


def changed(sample, **fields):
    rows = list(csv.DictReader(io.StringIO(sample.decode("utf-8")), delimiter=";"))
    rows[0].update(fields)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=list(rows[0]), delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


def parse(data, **kwargs):
    return parse_file(data, "sample.csv", "conceptos_v1", Settings(**kwargs))


@pytest.mark.parametrize(
    ("fields", "code"),
    [
        ({"importe": "70000.01"}, "TOTAL_MISMATCH"),
        ({"importe": "70000.001"}, "INVALID_MONEY"),
        ({"importe": "-70000.00"}, "INVALID_SIGN"),
        ({"concepto_codigo": "INVENTADO"}, "UNKNOWN_CONCEPT"),
        ({"periodo_inicio": "2026-10-01"}, "DATE_ORDER"),
        ({"fecha_vencimiento": "2026-02-30"}, "INVALID_DATE"),
        ({"moneda": "USD"}, "INVALID_CURRENCY"),
        ({"nombre_cliente": ""}, "REQUIRED_FIELD"),
    ],
)
def test_invalid_invoice_does_not_block_other_invoices(sample, fields, code):
    invoices = parse(changed(sample, **fields)).invoices
    assert code in {e.code for e in invoices[0].issues}
    assert all(not invoice.issues for invoice in invoices[1:])


def test_header_conflict_and_duplicate_line(sample):
    rows = sample.decode().splitlines()
    cells = rows[2].split(";")
    cells[8] = "105001.00"
    rows[2] = ";".join(cells)
    assert "HEADER_CONFLICT" in {e.code for e in parse("\n".join(rows).encode()).invoices[1].issues}
    rows = sample.decode().splitlines()
    rows.insert(2, rows[1])
    assert "DUPLICATE_LINE" in {e.code for e in parse("\n".join(rows).encode()).invoices[0].issues}


def test_preserves_zero_identifiers_and_source(sample):
    invoice = parse(sample).invoices[0]
    assert invoice.header["cuenta_id"] == "000001"
    assert invoice.lines[0].source.row == 2
    assert invoice.lines[0].source.raw == "70000.00"
    assert invoice.lines[0].amount == Decimal("70000.00")


def test_structural_and_limits(sample):
    for data, options, code in [
        (sample.replace(b"cliente_id;", b"otra_columna;", 1), {}, "INVALID_COLUMNS"),
        (sample, {"max_lines": 2}, "LINE_LIMIT"),
        (sample, {"max_invoices": 2}, "INVOICE_LIMIT"),
        (b"\xff", {}, "INVALID_CSV"),
    ]:
        with pytest.raises(InputError) as error:
            parse(data, **options)
        assert error.value.issues[0].code == code


def test_xlsx_formula_is_blocked(sample):
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "facturacion"
    for row in csv.reader(io.StringIO(sample.decode()), delimiter=";"):
        sheet.append(row)
    sheet["N2"] = "=70000"
    result = io.BytesIO()
    workbook.save(result)
    with pytest.raises(InputError) as error:
        parse_file(result.getvalue(), "test.xlsx", "conceptos_v1", Settings())
    assert error.value.issues[0].code == "FORMULA_NOT_ALLOWED"
    assert error.value.issues[0].row == 2
