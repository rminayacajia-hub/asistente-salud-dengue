"""
Pruebas del endpoint de salud (GET /health) y esquemas base.
"""
from fastapi.testclient import TestClient
from app.main import app
from app.schemas import HealthResponse

client = TestClient(app)


def test_health_check_status_code():
    """El endpoint /health debe responder con código HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200


def test_health_check_payload_structure():
    """El payload de /health debe cumplir con el esquema HealthResponse."""
    response = client.get("/health")
    data = response.json()
    validated = HealthResponse(**data)
    assert validated.status == "ok"
    assert validated.service == "asistente-dengue-backend"
    assert validated.version == "1.0.0"
    assert "environment" in data
    assert "timestamp" in data


def test_root_endpoint():
    """El endpoint raíz / debe responder con código HTTP 200 y mensaje de bienvenida."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["estado"] == "operativo"
    assert "/health" in data["salud"]
