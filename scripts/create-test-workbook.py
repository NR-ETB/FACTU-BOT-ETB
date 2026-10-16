"""Fixture XLSX equivalente al CSV; no contiene datos reales ni fórmulas."""

import csv
from pathlib import Path

from openpyxl import Workbook

root = Path(__file__).resolve().parents[1]
fixture = root / "tests" / "fixtures" / "cinco_clientes.csv"
workbook = Workbook()
sheet = workbook.active
sheet.title = "facturacion"
with fixture.open(encoding="utf-8", newline="") as source:
    for row in csv.reader(source, delimiter=";"):
        sheet.append(row)
sheet.freeze_panes = "A2"
sheet.auto_filter.ref = sheet.dimensions
for column in sheet.columns:
    sheet.column_dimensions[column[0].column_letter].width = min(
        max(len(str(cell.value or "")) for cell in column) + 2, 48
    )
workbook.save(fixture.with_suffix(".xlsx"))
workbook.close()
