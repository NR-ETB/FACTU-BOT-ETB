import io
import json
import logging
import threading
import zipfile
from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from sqlalchemy import delete, select

from videofacturacion.config import Settings
from videofacturacion.domain.models import Invoice
from videofacturacion.domain.money import cents, parse_money
from videofacturacion.ingestion.reader import InputError, parse_file
from videofacturacion.persistence.database import create_database
from videofacturacion.persistence.models import (
    ImportRecord,
    InvoiceRecord,
    LineRecord,
    ReviewRecord,
    ScriptRecord,
    uid,
)
from videofacturacion.scripts.engine import ScriptEngine, canonical_hash
from videofacturacion.storage.files import LocalFileStore

logger = logging.getLogger("videofacturacion")


class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


class BillingService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.engine, self.sessions = create_database(settings.data_dir)
        self.scripts = ScriptEngine()
        self.lock = threading.RLock()
        self.storage = LocalFileStore(settings.data_dir / "sources")
        self.sources = self.storage.root
        with self.sessions() as session:
            self.storage.recover_deletions(
                lambda identifier: session.get(ImportRecord, identifier) is not None
            )
        with self.sessions.begin() as session:
            for script in session.scalars(
                select(ScriptRecord).where(ScriptRecord.signature != self.scripts.signature)
            ):
                script.status = "OBSOLETO"

    @staticmethod
    def required(session, model, identifier):
        record = session.get(model, identifier)
        if record is None:
            raise ServiceError("NOT_FOUND", "Recurso no encontrado.", 404)
        return record

    def import_file(self, data: bytes, filename: str, profile: str) -> dict:
        digest = sha256(data).hexdigest()
        with self.lock:
            with self.sessions() as session:
                previous = session.scalar(
                    select(ImportRecord).where(
                        ImportRecord.file_hash == digest, ImportRecord.profile == profile
                    )
                )
                if previous:
                    return dict(self.get_import(previous.id), reused=True)
            issues, invoices = [], []
            try:
                invoices = parse_file(data, filename, profile, self.settings).invoices
            except InputError as error:
                issues = [asdict(issue) for issue in error.issues]
            identifier = uid()
            suffix = Path(filename).suffix.lower()
            if suffix not in (".csv", ".xlsx"):
                suffix = ".bin"
            path = self.storage.save(identifier, suffix, data)
            try:
                with self.sessions.begin() as session:
                    session.add(
                        ImportRecord(
                            id=identifier,
                            file_hash=digest,
                            suffix=suffix,
                            profile=profile,
                            issues=issues,
                        )
                    )
                    session.flush()
                    for invoice in invoices:
                        # Una fuente nueva es una versión nueva; nunca modifica la anterior.
                        previous_versions = session.scalars(
                            select(InvoiceRecord).where(
                                InvoiceRecord.logical_key == invoice.key,
                                InvoiceRecord.current.is_(True),
                            )
                        ).all()
                        for previous in previous_versions:
                            previous.current = False
                            for script in session.scalars(
                                select(ScriptRecord).where(ScriptRecord.invoice_id == previous.id)
                            ):
                                script.status = "OBSOLETO"
                        try:
                            total = cents(parse_money(invoice.header["total_fuente"]))
                        except ValueError:
                            total = None
                        record = InvoiceRecord(
                            import_id=identifier,
                            logical_key=invoice.key,
                            content_hash=canonical_hash(invoice.snapshot()),
                            current=True,
                            status="INVALIDA" if invoice.issues else "VALIDA",
                            total_cents=total,
                            calculated_cents=cents(invoice.calculated),
                            snapshot=invoice.snapshot(),
                            issues=[asdict(issue) for issue in invoice.issues],
                        )
                        session.add(record)
                        session.flush()
                        for line in invoice.lines:
                            session.add(
                                LineRecord(
                                    invoice_id=record.id,
                                    line_key=line.line_id,
                                    amount_cents=cents(line.amount),
                                    source=asdict(line.source),
                                )
                            )
            except Exception:
                path.unlink(missing_ok=True)
                raise
        logger.info(
            json.dumps(
                {
                    "event": "import_completed",
                    "import_id": identifier,
                    "invoice_count": len(invoices),
                    "structural_errors": len(issues),
                }
            )
        )
        return dict(self.get_import(identifier), reused=False)

    def invoice_view(self, record: InvoiceRecord) -> dict:
        return {
            "id": record.id,
            "import_id": record.import_id,
            "key": record.logical_key,
            "current": record.current,
            "status": record.status,
            "created_at": record.created_at,
            "total": None if record.total_cents is None else self.decimal_cents(record.total_cents),
            "calculated": self.decimal_cents(record.calculated_cents),
            "source": record.snapshot,
            "issues": record.issues,
            "content_hash": record.content_hash,
        }

    @staticmethod
    def decimal_cents(value: int) -> str:
        sign = "-" if value < 0 else ""
        whole, minor = divmod(abs(value), 100)
        return f"{sign}{whole}.{minor:02d}"

    def list_imports(self) -> list[dict]:
        with self.sessions() as session:
            ids = list(
                session.scalars(select(ImportRecord.id).order_by(ImportRecord.created_at.desc()))
            )
        return [self.get_import(identifier) for identifier in ids]

    def get_import(self, identifier: str) -> dict:
        with self.sessions() as session:
            record = self.required(session, ImportRecord, identifier)
            invoices = session.scalars(
                select(InvoiceRecord).where(InvoiceRecord.import_id == identifier)
            ).all()
            valid = sum(i.status == "VALIDA" for i in invoices)
            return {
                "id": identifier,
                "file_hash": record.file_hash,
                "profile": record.profile,
                "filename": identifier + record.suffix,
                "created_at": record.created_at,
                "issues": record.issues,
                "invoice_ids": [i.id for i in invoices],
                "valid": valid,
                "invalid": len(invoices) - valid,
                "status": "RECHAZADO"
                if record.issues
                else ("VALIDADO" if valid == len(invoices) else "CON_ERRORES"),
            }

    def list_invoices(self, import_id: str | None = None) -> list[dict]:
        with self.sessions() as session:
            statement = select(InvoiceRecord).order_by(InvoiceRecord.created_at)
            if import_id:
                self.required(session, ImportRecord, import_id)
                statement = statement.where(InvoiceRecord.import_id == import_id)
            return [self.invoice_view(record) for record in session.scalars(statement)]

    def get_invoice(self, identifier: str) -> dict:
        with self.sessions() as session:
            return self.invoice_view(self.required(session, InvoiceRecord, identifier))

    def generate(self, identifiers: list[str]) -> dict:
        results = []
        for identifier in dict.fromkeys(identifiers):
            try:
                with self.lock, self.sessions.begin() as session:
                    invoice = self.required(session, InvoiceRecord, identifier)
                    if invoice.status != "VALIDA" or not invoice.current:
                        raise ServiceError("INVOICE_BLOCKED", "La factura es inválida u obsoleta.")
                    previous = session.scalar(
                        select(ScriptRecord).where(
                            ScriptRecord.invoice_id == identifier,
                            ScriptRecord.signature == self.scripts.signature,
                        )
                    )
                    if previous:
                        script_id = previous.id
                        reused = True
                    else:
                        # Cambios de reglas o plantilla no conservan aprobaciones.
                        for old in session.scalars(
                            select(ScriptRecord).where(ScriptRecord.invoice_id == identifier)
                        ):
                            old.status = "OBSOLETO"
                        payload = self.scripts.generate(Invoice.from_snapshot(invoice.snapshot))
                        script = ScriptRecord(
                            invoice_id=identifier, signature=self.scripts.signature, payload=payload
                        )
                        session.add(script)
                        session.flush()
                        script_id, reused = script.id, False
                results.append({"invoice_id": identifier, "script_id": script_id, "reused": reused})
            except ServiceError as error:
                results.append(
                    {
                        "invoice_id": identifier,
                        "error": {"code": error.code, "message": error.message},
                    }
                )
        return {"results": results}

    def effective_status(self, record: ScriptRecord, invoice: InvoiceRecord) -> str:
        if not invoice.current or record.signature != self.scripts.signature:
            return "OBSOLETO"
        if self.scripts.verify(Invoice.from_snapshot(invoice.snapshot), record.payload):
            return "BLOQUEADO"
        return record.status

    def get_script(self, identifier: str) -> dict:
        with self.sessions() as session:
            record = self.required(session, ScriptRecord, identifier)
            invoice = self.required(session, InvoiceRecord, record.invoice_id)
            reviews = session.scalars(
                select(ReviewRecord)
                .where(ReviewRecord.script_id == identifier)
                .order_by(ReviewRecord.created_at)
            ).all()
            return {
                "id": record.id,
                "invoice_id": record.invoice_id,
                "status": self.effective_status(record, invoice),
                "created_at": record.created_at,
                "payload": record.payload,
                "reviews": [
                    {
                        "id": r.id,
                        "decision": r.decision,
                        "reason": r.reason,
                        "operator": r.operator,
                        "created_at": r.created_at,
                    }
                    for r in reviews
                ],
            }

    def list_scripts(self, invoice_id: str | None = None) -> list[dict]:
        with self.sessions() as session:
            statement = select(ScriptRecord.id).order_by(ScriptRecord.created_at)
            if invoice_id:
                self.required(session, InvoiceRecord, invoice_id)
                statement = statement.where(ScriptRecord.invoice_id == invoice_id)
            ids = list(session.scalars(statement))
        return [self.get_script(identifier) for identifier in ids]

    def review(self, identifier: str, decision: str, reason: str, operator: str) -> dict:
        if decision not in ("APROBADO", "RECHAZADO") or not operator.strip():
            raise ServiceError("INVALID_REVIEW", "Decisión u operador inválido.", 422)
        if decision == "RECHAZADO" and not reason.strip():
            raise ServiceError("REASON_REQUIRED", "Indique el motivo del rechazo.", 422)
        with self.lock, self.sessions.begin() as session:
            record = self.required(session, ScriptRecord, identifier)
            invoice = self.required(session, InvoiceRecord, record.invoice_id)
            if self.effective_status(record, invoice) in ("OBSOLETO", "BLOQUEADO"):
                raise ServiceError(
                    "SCRIPT_BLOCKED", "El guion cambió o su fuente ya no está vigente."
                )
            record.status = decision
            session.add(
                ReviewRecord(
                    script_id=identifier,
                    decision=decision,
                    reason=reason.strip(),
                    operator=operator.strip(),
                )
            )
        logger.info(
            json.dumps({"event": "script_reviewed", "script_id": identifier, "decision": decision})
        )
        return self.get_script(identifier)

    def export(self, import_id: str) -> bytes:
        imported = self.get_import(import_id)
        invoices = self.list_invoices(import_id)
        scripts = [script for invoice in invoices for script in self.list_scripts(invoice["id"])]
        result = io.BytesIO()
        with zipfile.ZipFile(result, "w", zipfile.ZIP_DEFLATED) as archive:
            report = {"import": imported, "invoices": invoices, "scripts": scripts}
            archive.writestr("informe.json", json.dumps(report, ensure_ascii=False, indent=2))
            for script in scripts:
                # Guiones inválidos/obsoletos solo figuran en el informe histórico.
                if script["status"] not in ("BLOQUEADO", "OBSOLETO"):
                    archive.writestr(
                        f"guiones/{script['status']}/{script['id']}.txt", script["payload"]["text"]
                    )
        return result.getvalue()

    def delete_import(self, identifier: str) -> None:
        with self.lock:
            staged = None
            try:
                with self.sessions.begin() as session:
                    record = self.required(session, ImportRecord, identifier)
                    staged = self.storage.stage_delete(record.id, record.suffix)
                    session.execute(delete(ImportRecord).where(ImportRecord.id == identifier))
            except Exception:
                if staged:
                    self.storage.rollback_delete(*staged)
                raise
            try:
                self.storage.finish_delete(staged[1])
            except OSError:
                logger.error(
                    json.dumps({"event": "deletion_cleanup_pending", "import_id": identifier})
                )
                raise ServiceError(
                    "DELETION_CLEANUP_PENDING",
                    "Los registros se eliminaron; queda un archivo pendiente. Reinicie la API para completar su eliminación.",
                    503,
                ) from None
        # No se reactiva una aprobación antigua al borrar una fuente posterior.
        logger.info(json.dumps({"event": "import_deleted", "import_id": identifier}))
