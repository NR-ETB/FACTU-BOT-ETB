import json
import logging
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field
from starlette.concurrency import run_in_threadpool

from videofacturacion.application.service import BillingService, ServiceError
from videofacturacion.config import Settings


class BatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    invoice_ids: list[str] = Field(min_length=1, max_length=100)


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: Literal["APROBADO", "RECHAZADO"]
    reason: str = Field(default="", max_length=1000)
    operator: str = Field(default="operador-local", min_length=1, max_length=80)


def create_app(settings: Settings | None = None) -> FastAPI:
    configuration = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        logger = logging.getLogger("videofacturacion")
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        app.state.service = BillingService(configuration)
        try:
            yield
        finally:
            app.state.service.engine.dispose()

    app = FastAPI(title="Videofacturación ETB · Fase 1", version="0.1.0", lifespan=lifespan)

    @app.exception_handler(ServiceError)
    async def service_error(request, error):
        return JSONResponse(
            {"error": {"code": error.code, "message": error.message}}, status_code=error.status
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # FastAPI incluye el valor rechazado por defecto; no reflejar contenido personal.
        return JSONResponse(
            {
                "error": {
                    "code": "INVALID_REQUEST",
                    "message": "Solicitud inválida.",
                    "fields": [
                        {"location": list(e["loc"]), "type": e["type"]} for e in error.errors()
                    ],
                }
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request, error):
        logging.getLogger("videofacturacion").error(
            json.dumps({"event": "internal_error", "type": type(error).__name__})
        )
        return JSONResponse(
            {
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Error interno; revise el estado antes de repetir.",
                }
            },
            status_code=500,
        )

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "phase": 1, "audiovisual_enabled": False}

    @app.post("/api/v1/imports", status_code=201)
    async def import_file(
        request: Request,
        file: UploadFile = File(),
        profile: Literal["conceptos_v1", "etb_prueba_v1"] = Form("conceptos_v1"),
        synthetic_confirmed: bool = Form(False),
    ):
        try:
            if not synthetic_confirmed:
                raise ServiceError(
                    "SYNTHETIC_ONLY",
                    "Confirme que el archivo contiene exclusivamente datos ficticios.",
                    422,
                )
            data = await file.read(configuration.max_bytes + 1)
            if len(data) > configuration.max_bytes:
                raise ServiceError("FILE_SIZE", "El archivo excede el límite permitido.", 413)
            return await run_in_threadpool(
                request.app.state.service.import_file, data, file.filename or "archivo", profile
            )
        finally:
            await file.close()

    @app.get("/api/v1/imports")
    def imports(request: Request):
        return request.app.state.service.list_imports()

    @app.get("/api/v1/imports/{identifier}")
    def get_import(identifier: str, request: Request):
        return request.app.state.service.get_import(identifier)

    @app.delete("/api/v1/imports/{identifier}", status_code=204)
    def delete_import(identifier: str, request: Request):
        request.app.state.service.delete_import(identifier)
        return Response(status_code=204)

    @app.get("/api/v1/invoices")
    def invoices(request: Request, import_id: str | None = Query(None)):
        return request.app.state.service.list_invoices(import_id)

    @app.get("/api/v1/invoices/{identifier}")
    def invoice(identifier: str, request: Request):
        return request.app.state.service.get_invoice(identifier)

    @app.post("/api/v1/scripts/batch")
    def scripts_batch(body: BatchRequest, request: Request):
        return request.app.state.service.generate(body.invoice_ids)

    @app.get("/api/v1/scripts")
    def scripts(request: Request, invoice_id: str | None = Query(None)):
        return request.app.state.service.list_scripts(invoice_id)

    @app.get("/api/v1/scripts/{identifier}")
    def script(identifier: str, request: Request):
        return request.app.state.service.get_script(identifier)

    @app.post("/api/v1/scripts/{identifier}/reviews")
    def review(identifier: str, body: ReviewRequest, request: Request):
        return request.app.state.service.review(
            identifier, body.decision, body.reason, body.operator
        )

    @app.get("/api/v1/imports/{identifier}/export")
    def export(identifier: str, request: Request):
        return Response(
            request.app.state.service.export(identifier),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="informe-{identifier}.zip"'},
        )

    return app


app = create_app()
