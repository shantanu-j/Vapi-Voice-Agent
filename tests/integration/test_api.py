from fastapi.testclient import TestClient
from main import app
from config.settings import VAPI_SERVER_SECRET


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy"
    }


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "message": "Statfinity AI backend is running",
    }


def test_protected_endpoint_requires_secret():
    response = client.post(
        "/check_availability/",
        json={
            "start_date_time": "2026-09-15T10:00:00+00:00",
        },
    )

    assert response.status_code == 401


def test_protected_endpoint_accepts_valid_secret():
    response = client.post(
        "/check_availability/",
        headers={
            "x-webhook-secret": VAPI_SERVER_SECRET,
        },
        json={
            "start_date_time": "2026-09-15T10:00:00+00:00",
        },
    )

    assert response.status_code in (200, 400, 500)