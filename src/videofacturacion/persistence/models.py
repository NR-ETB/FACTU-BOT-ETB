from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import JSON, BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uid() -> str:
    return str(uuid4())


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class ImportRecord(Base):
    __tablename__ = "imports"
    __table_args__ = (UniqueConstraint("file_hash", "profile"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    file_hash: Mapped[str] = mapped_column(String, index=True)
    profile: Mapped[str] = mapped_column(String)
    suffix: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)
    issues: Mapped[list] = mapped_column(JSON, default=list)


class InvoiceRecord(Base):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    import_id: Mapped[str] = mapped_column(ForeignKey("imports.id", ondelete="CASCADE"), index=True)
    logical_key: Mapped[str] = mapped_column(String, index=True)
    content_hash: Mapped[str] = mapped_column(String, index=True)
    current: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String)
    total_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    calculated_cents: Mapped[int] = mapped_column(BigInteger)
    snapshot: Mapped[dict] = mapped_column(JSON)
    issues: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)


class LineRecord(Base):
    __tablename__ = "invoice_lines"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    line_key: Mapped[str] = mapped_column(String)
    amount_cents: Mapped[int] = mapped_column(BigInteger)
    source: Mapped[dict] = mapped_column(JSON)


class ScriptRecord(Base):
    __tablename__ = "scripts"
    __table_args__ = (UniqueConstraint("invoice_id", "signature"),)
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    invoice_id: Mapped[str] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    signature: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="VALIDADO")
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)


class ReviewRecord(Base):
    __tablename__ = "reviews"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    script_id: Mapped[str] = mapped_column(ForeignKey("scripts.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String)
    reason: Mapped[str] = mapped_column(String)
    operator: Mapped[str] = mapped_column(String)
    created_at: Mapped[str] = mapped_column(String, default=timestamp)
