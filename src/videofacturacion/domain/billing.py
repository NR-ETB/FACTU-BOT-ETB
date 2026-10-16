from videofacturacion.domain.models import Invoice, Issue

# Código -> signo permitido. Descripciones de origen se muestran como datos, no instrucciones.
CATALOG = {
    "INTERNET": 1,
    "TELEVISION": 1,
    "TELEFONIA": 1,
    "CARGO": 1,
    "IMPUESTO": 1,
    "SALDO_ANTERIOR": 1,
    "OTROS_CARGOS": 1,
    "DESCUENTO": -1,
    "ABONO": -1,
    "PAGO": -1,
}


def reconcile(invoice: Invoice) -> None:
    seen = set()
    for line in invoice.lines:
        ref = line.source
        issue = None
        if line.line_id in seen:
            issue = ("DUPLICATE_LINE", "Identificador de línea repetido en la factura.")
        elif line.code not in CATALOG:
            issue = ("UNKNOWN_CONCEPT", "Concepto no incluido en el catálogo v1.")
        elif line.amount * CATALOG[line.code] < 0:
            issue = ("INVALID_SIGN", "El signo no corresponde al sentido financiero del concepto.")
        seen.add(line.line_id)
        if issue:
            invoice.issues.append(
                Issue(
                    *issue, row=ref.row, sheet=ref.sheet, field=ref.field, invoice_key=invoice.key
                )
            )
    if not invoice.issues and invoice.calculated != invoice.total:
        ref = invoice.refs["total_fuente"]
        invoice.issues.append(
            Issue(
                "TOTAL_MISMATCH",
                "La suma de conceptos no coincide exactamente con el total fuente.",
                row=ref.row,
                field=ref.field,
                sheet=ref.sheet,
                invoice_key=invoice.key,
            )
        )
