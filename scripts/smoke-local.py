"""Arranca y detiene servidores locales propios para comprobar HTTP real; sin despliegue."""

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

import httpx


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    root = Path(__file__).resolve().parents[1]
    output = root / ".cache" / ("live-smoke-" + str(uuid4()))
    output.mkdir(parents=True)
    api_port, ui_port = free_port(), free_port()
    environment = dict(
        os.environ,
        ETB_DATA_DIR=str(output / "data"),
        ETB_API_URL=f"http://127.0.0.1:{api_port}",
        PYTHONIOENCODING="utf-8",
        PYTHONUTF8="1",
    )
    commands = [
        [
            sys.executable,
            "-m",
            "uvicorn",
            "videofacturacion.api.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(api_port),
            "--no-access-log",
        ],
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            "src/videofacturacion/ui/app.py",
            "--server.address",
            "127.0.0.1",
            "--server.port",
            str(ui_port),
            "--browser.gatherUsageStats",
            "false",
            "--server.headless",
            "true",
        ],
    ]
    processes, logs = [], []
    try:
        for index, command in enumerate(commands):
            log = (output / f"server-{index}.log").open("w", encoding="utf-8")
            logs.append(log)
            processes.append(
                subprocess.Popen(
                    command,
                    cwd=root,
                    env=environment,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            )
        with httpx.Client(timeout=2, trust_env=False) as client:
            urls = [
                f"http://127.0.0.1:{api_port}/api/v1/health",
                f"http://127.0.0.1:{ui_port}/_stcore/health",
            ]
            for url in urls:
                deadline = time.monotonic() + 25
                while True:
                    try:
                        response = client.get(url)
                        if response.status_code == 200:
                            break
                    except httpx.HTTPError:
                        pass
                    if time.monotonic() > deadline or any(p.poll() is not None for p in processes):
                        raise RuntimeError(f"El servidor local no inició; revisar {output}")
                    time.sleep(0.2)
            assert client.get(f"http://127.0.0.1:{ui_port}/").status_code == 200
            sample = (root / "tests/fixtures/cinco_clientes.csv").read_bytes()
            imported = client.post(
                f"http://127.0.0.1:{api_port}/api/v1/imports",
                files={"file": ("cinco_clientes.csv", sample)},
                data={"profile": "conceptos_v1", "synthetic_confirmed": "true"},
            )
            imported.raise_for_status()
            assert imported.json()["valid"] == 5
            batch = client.post(
                f"http://127.0.0.1:{api_port}/api/v1/scripts/batch",
                json={"invoice_ids": imported.json()["invoice_ids"]},
            )
            batch.raise_for_status()
            assert len(batch.json()["results"]) == 5
        print(
            json.dumps(
                {
                    "api_http": "ok",
                    "streamlit_http": "ok",
                    "invoices": 5,
                    "scripts": 5,
                    "external_generation_calls": 0,
                }
            )
        )
    finally:
        for process in processes:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for log in logs:
            log.close()


if __name__ == "__main__":
    main()
