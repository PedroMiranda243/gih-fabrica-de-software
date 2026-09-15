"""Testes da verificação de saúde."""
from fastapi.testclient import TestClient

from app.main import app

cliente = TestClient(app, raise_server_exceptions=False)


def test_health_responde_ok():
    r = cliente.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_health_informa_estado_do_banco():
    """O campo existe mesmo com o banco fora — é diagnóstico, não erro."""
    corpo = cliente.get("/api/health").json()
    assert corpo["banco"] in {"ok", "indisponível"}


def test_health_nao_exige_sessao():
    """Único endpoint público do sistema (RF05)."""
    assert cliente.get("/api/health").status_code == 200
