from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from videofacturacion.api.main import create_app
from videofacturacion.config import Settings

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(Settings(data_dir=tmp_path / "data"))) as client:
        yield client


@pytest.fixture
def sample():
    return (FIXTURES / "cinco_clientes.csv").read_bytes()


def upload(client, data, filename="sample.csv", profile="conceptos_v1"):
    response = client.post(
        "/api/v1/imports",
        files={"file": (filename, data)},
        data={"profile": profile, "synthetic_confirmed": "true"},
    )
    assert response.status_code == 201, response.text
    return response.json()
