import json
from collections import Counter
from dataclasses import asdict
from datetime import date
from hashlib import sha256
from importlib.resources import files

from jinja2 import Environment, PackageLoader, StrictUndefined

from videofacturacion.domain.billing import CATALOG
from videofacturacion.domain.models import RULES_VERSION, Invoice
from videofacturacion.domain.money import money_words, number_words, parse_money

TEMPLATE_VERSION = "guion-es-CO-v1"
_MONTHS = (
    "",
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


def canonical_hash(value) -> str:
    return sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def date_words(text: str) -> str:
    value = date.fromisoformat(text)
    day = "primero" if value.day == 1 else number_words(value.day)
    return f"{day} de {_MONTHS[value.month]} de {number_words(value.year)}"


class ScriptEngine:
    def __init__(self):
        self.environment = Environment(
            loader=PackageLoader("videofacturacion.scripts", "templates"),
            undefined=StrictUndefined,
            autoescape=False,
        )
        self.template_hash = canonical_hash(
            {
                name: self.environment.loader.get_source(self.environment, name)[0]
                for name in sorted(self.environment.list_templates())
            }
        )
        self.code_hash = canonical_hash(
            {
                name: (files("videofacturacion") / name).read_text(encoding="utf-8")
                for name in ("domain/billing.py", "domain/money.py", "scripts/engine.py")
            }
        )

    @property
    def signature(self) -> str:
        return canonical_hash(
            [RULES_VERSION, CATALOG, TEMPLATE_VERSION, self.template_hash, self.code_hash]
        )

    def render(self, template: str, **values) -> str:
        return self.environment.get_template(template + ".j2").render(**values).strip()

    def generate(self, invoice: Invoice) -> dict:
        if invoice.issues:
            raise ValueError("No se puede narrar una factura inválida.")
        h = invoice.header
        segments = [
            {
                "kind": "greeting",
                "text": self.render(
                    "greeting",
                    name=h["nombre_cliente"],
                    start=date_words(h["periodo_inicio"]),
                    end=date_words(h["periodo_fin"]),
                ),
                "bindings": ["nombre_cliente", "periodo_inicio", "periodo_fin"],
            }
        ]
        evidence = []
        for line in invoice.lines:
            spoken = money_words(abs(line.amount))
            action = {"DESCUENTO": "un descuento", "PAGO": "un pago"}.get(line.code, "un abono")
            segment = {
                "kind": "line",
                "line_id": line.line_id,
                "code": line.code,
                "amount": format(line.amount, ".2f"),
                "spoken": spoken,
                "source": asdict(line.source),
                "text": self.render(
                    "line",
                    negative=CATALOG[line.code] < 0,
                    action=action,
                    description=line.description,
                    service=line.service,
                    spoken=spoken,
                ),
            }
            segments.append(segment)
            evidence.append(
                {
                    "kind": "line",
                    "line_id": line.line_id,
                    "source": asdict(line.source),
                    "normalized": format(line.amount, ".2f"),
                    "spoken": spoken,
                    "financial_sense": "RESTA" if CATALOG[line.code] < 0 else "SUMA",
                    "verified": True,
                }
            )
        total_spoken = money_words(abs(invoice.total))
        segments.append(
            {
                "kind": "total",
                "amount": format(invoice.total, ".2f"),
                "spoken": total_spoken,
                "source": asdict(invoice.refs["total_fuente"]),
                "text": self.render("total", spoken=total_spoken, negative=invoice.total < 0),
            }
        )
        segments.append(
            {
                "kind": "due",
                "bindings": ["fecha_vencimiento"],
                "text": self.render("due", due=date_words(h["fecha_vencimiento"])),
            }
        )
        for name in (
            "nombre_cliente",
            "periodo_inicio",
            "periodo_fin",
            "fecha_vencimiento",
            "total_fuente",
        ):
            normalized = h[name]
            spoken = (
                total_spoken
                if name == "total_fuente"
                else (normalized if name == "nombre_cliente" else date_words(normalized))
            )
            evidence.append(
                {
                    "kind": "header",
                    "field": name,
                    "source": asdict(invoice.refs[name]),
                    "normalized": normalized,
                    "spoken": spoken,
                    "verified": True,
                }
            )
        script = {
            "template_version": TEMPLATE_VERSION,
            "template_hash": self.template_hash,
            "rules_version": RULES_VERSION,
            "signature": self.signature,
            "source_hash": canonical_hash(invoice.snapshot()),
            "segments": segments,
            "text": "\n\n".join(segment["text"] for segment in segments),
            "evidence": evidence,
        }
        errors = self.verify(invoice, script)
        if errors:
            raise ValueError("El guion generado no superó su verificación: " + ", ".join(errors))
        return script

    def verify(self, invoice: Invoice, script: dict) -> list[str]:
        """Bloqueo antes de guardar, exportar y aprobar; no usa un modelo generativo."""
        errors = []
        if invoice.issues or invoice.calculated != invoice.total:
            errors.append("INVALID_INVOICE")
        if script.get("signature") != self.signature:
            errors.append("STALE_TEMPLATE")
        if script.get("source_hash") != canonical_hash(invoice.snapshot()):
            errors.append("SOURCE_CHANGED")
        segments = script.get("segments", [])
        line_segments = [s for s in segments if s.get("kind") == "line"]
        if Counter(s.get("line_id") for s in line_segments) != Counter(
            x.line_id for x in invoice.lines
        ):
            errors.append("LINE_COVERAGE")
        lines = {line.line_id: line for line in invoice.lines}
        for segment in line_segments:
            line = lines.get(segment.get("line_id"))
            if line is None:
                continue
            expected_text = self.render(
                "line",
                negative=CATALOG.get(line.code, 1) < 0,
                action={"DESCUENTO": "un descuento", "PAGO": "un pago"}.get(line.code, "un abono"),
                description=line.description,
                service=line.service,
                spoken=money_words(abs(line.amount)),
            )
            if (
                segment.get("amount") != format(line.amount, ".2f")
                or segment.get("code") != line.code
                or segment.get("text") != expected_text
                or segment.get("spoken") != money_words(abs(line.amount))
                or segment.get("source") != asdict(line.source)
            ):
                errors.append("LINE_CHANGED")
            raw_amount = parse_money(line.source.raw.strip())
            if line.source.field == "descuento":
                raw_amount = -raw_amount
            if raw_amount != line.amount:
                errors.append("SOURCE_AMOUNT_MISMATCH")
        h = invoice.header
        expected_header = [
            (
                "greeting",
                self.render(
                    "greeting",
                    name=h["nombre_cliente"],
                    start=date_words(h["periodo_inicio"]),
                    end=date_words(h["periodo_fin"]),
                ),
            ),
            (
                "total",
                self.render(
                    "total", spoken=money_words(abs(invoice.total)), negative=invoice.total < 0
                ),
            ),
            ("due", self.render("due", due=date_words(h["fecha_vencimiento"]))),
        ]
        for kind, text in expected_header:
            matches = [s for s in segments if s.get("kind") == kind]
            if len(matches) != 1 or matches[0].get("text") != text:
                errors.append("HEADER_CHANGED")
        if [s.get("kind") for s in segments] != ["greeting"] + ["line"] * len(invoice.lines) + [
            "total",
            "due",
        ]:
            errors.append("SEGMENT_ORDER")
        if script.get("text") != "\n\n".join(s.get("text", "") for s in segments):
            errors.append("TEXT_CHANGED")
        if parse_money(invoice.refs["total_fuente"].raw.strip()) != invoice.total:
            errors.append("SOURCE_TOTAL_MISMATCH")
        totals = [s for s in segments if s.get("kind") == "total"]
        if len(totals) == 1 and (
            totals[0].get("amount") != format(invoice.total, ".2f")
            or totals[0].get("spoken") != money_words(abs(invoice.total))
            or totals[0].get("source") != asdict(invoice.refs["total_fuente"])
        ):
            errors.append("TOTAL_BINDING_CHANGED")
        expected_evidence = [
            {
                "kind": "line",
                "line_id": line.line_id,
                "source": asdict(line.source),
                "normalized": format(line.amount, ".2f"),
                "spoken": money_words(abs(line.amount)),
                "financial_sense": "RESTA" if CATALOG[line.code] < 0 else "SUMA",
                "verified": True,
            }
            for line in invoice.lines
        ]
        for name in (
            "nombre_cliente",
            "periodo_inicio",
            "periodo_fin",
            "fecha_vencimiento",
            "total_fuente",
        ):
            raw = invoice.refs[name].raw.strip()
            if name != "total_fuente" and raw != h[name]:
                errors.append("SOURCE_HEADER_MISMATCH")
            expected_evidence.append(
                {
                    "kind": "header",
                    "field": name,
                    "source": asdict(invoice.refs[name]),
                    "normalized": h[name],
                    "spoken": money_words(abs(invoice.total))
                    if name == "total_fuente"
                    else (h[name] if name == "nombre_cliente" else date_words(h[name])),
                    "verified": True,
                }
            )
        if script.get("evidence") != expected_evidence:
            errors.append("EVIDENCE_CHANGED")
        return sorted(set(errors))
