"""Demostración reproducible en proceso: usa la API sin servidor ni acceso a red."""

import argparse
import json
import platform
import time
from pathlib import Path

from fastapi.testclient import TestClient

from videofacturacion.api.main import create_app
from videofacturacion.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path)
    parser.add_argument(
        "--profile", choices=["conceptos_v1", "etb_prueba_v1"], default="conceptos_v1"
    )
    parser.add_argument("--confirm-synthetic", action="store_true")
    parser.add_argument("--data-dir", type=Path, default=Path("var/demo"))
    args = parser.parse_args()
    if args.file and not args.confirm_synthetic:
        parser.error(
            "Para un archivo externo debe confirmar datos ficticios con --confirm-synthetic."
        )
    files = (
        [args.file]
        if args.file
        else [Path("tests/fixtures/cinco_clientes.csv"), Path("tests/fixtures/cinco_clientes.xlsx")]
    )
    started = time.perf_counter()
    summaries = []
    with TestClient(create_app(Settings(data_dir=args.data_dir))) as client:
        for path in files:
            with path.open("rb") as source:
                response = client.post(
                    "/api/v1/imports",
                    files={"file": (path.name, source)},
                    data={"profile": args.profile, "synthetic_confirmed": "true"},
                )
            response.raise_for_status()
            imported = response.json()
            response = client.post(
                "/api/v1/scripts/batch", json={"invoice_ids": imported["invoice_ids"]}
            )
            response.raise_for_status()
            generated = response.json()["results"]
            if imported["status"] != "VALIDADO" or any("error" in item for item in generated):
                raise SystemExit(
                    "Demostración bloqueada: consulte la importación y sus errores en la interfaz."
                )
            scripts = [
                client.get("/api/v1/scripts/" + item["script_id"]).json() for item in generated
            ]
            target = args.data_dir / f"informe-{imported['id']}.zip"
            exported = client.get(f"/api/v1/imports/{imported['id']}/export")
            exported.raise_for_status()
            target.write_bytes(exported.content)
            summaries.append(
                {
                    "format": path.suffix,
                    "import_id": imported["id"],
                    "invoices": imported["valid"],
                    "scripts": len(scripts),
                    "verified_bindings": sum(len(s["payload"]["evidence"]) for s in scripts),
                    "report": str(target.resolve()),
                }
            )
    summary = {
        "phase": 1,
        "external_generation_calls": 0,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "environment": {
            "python": platform.python_version(),
            "system": platform.system(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "results": summaries,
    }
    (args.data_dir / "ultima-demostracion.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
