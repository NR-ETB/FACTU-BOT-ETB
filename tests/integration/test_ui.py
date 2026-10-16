from pathlib import Path

import httpx
from conftest import upload
from streamlit.testing.v1 import AppTest

UI = Path(__file__).parents[2] / "src/videofacturacion/ui/app.py"


def click(app, label):
    return next(button for button in app.button if button.label == label).click().run()


def test_ui_batch_review_and_export(client, sample, monkeypatch):
    imported = upload(client, sample)

    class LocalClient:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, method, path, **kwargs):
            return client.request(method, "/api/v1" + path, **kwargs)

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: LocalClient())
    app = AppTest.from_file(str(UI), default_timeout=20).run()
    assert not app.exception
    app = click(app, "Generar guiones del lote")
    assert not app.exception
    scripts = client.get("/api/v1/scripts").json()
    assert len(scripts) == 5
    app = click(app, "Registrar revisión")
    assert not app.exception
    assert client.get("/api/v1/scripts/" + scripts[0]["id"]).json()["status"] == "APROBADO"
    app = click(app, "Preparar ZIP de guiones e informe")
    assert not app.exception
    assert any(element.label == "Descargar resultados" for element in app.get("download_button"))
    assert client.get(f"/api/v1/imports/{imported['id']}").json()["valid"] == 5


def test_ui_explains_api_unavailable(monkeypatch):
    class UnavailableClient:
        def __enter__(self):
            raise httpx.ConnectError("offline")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(httpx, "Client", lambda **kwargs: UnavailableClient())
    app = AppTest.from_file(str(UI), default_timeout=20).run()
    assert not app.exception
    assert any("No hay conexión" in error.value for error in app.error)
