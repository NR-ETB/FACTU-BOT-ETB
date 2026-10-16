from dataclasses import asdict, dataclass, field
from decimal import Decimal
from typing import Any

RULES_VERSION = "billing-v1"
SCHEMA_VERSION = "invoice-v1"


@dataclass(frozen=True)
class SourceRef:
    file_hash: str
    sheet: str
    row: int
    field: str
    raw: str


@dataclass(frozen=True)
class Issue:
    code: str
    message: str
    row: int | None = None
    field: str | None = None
    sheet: str | None = None
    invoice_key: str | None = None
    severity: str = "ERROR"


@dataclass(frozen=True)
class Line:
    line_id: str
    service: str
    code: str
    description: str
    amount: Decimal
    source: SourceRef


@dataclass
class Invoice:
    key: str
    header: dict[str, str]
    refs: dict[str, SourceRef]
    lines: list[Line] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return Decimal(self.header["total_fuente"])

    @property
    def calculated(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0.00"))

    def snapshot(self) -> dict[str, Any]:
        return {
            "header": self.header,
            "refs": {k: asdict(v) for k, v in self.refs.items()},
            "lines": [dict(asdict(line), amount=format(line.amount, ".2f")) for line in self.lines],
            "rules_version": RULES_VERSION,
            "schema_version": SCHEMA_VERSION,
        }

    @classmethod
    def from_snapshot(cls, data: dict[str, Any]) -> "Invoice":
        h = data["header"]
        return cls(
            key=f"{h['cuenta_id']}:{h['factura_id']}",
            header=h,
            refs={k: SourceRef(**v) for k, v in data["refs"].items()},
            lines=[
                Line(
                    **dict(line, amount=Decimal(line["amount"]), source=SourceRef(**line["source"]))
                )
                for line in data["lines"]
            ],
        )
