import pytest


@pytest.mark.django_db
def test_health_endpoint(api_client):
    response = api_client.get("/api/health/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"]
    assert isinstance(body["version"], str)


@pytest.mark.django_db
def test_health_endpoint_extended(api_client):
    response = api_client.get("/api/health/?extended=1")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["checks"]["database"] == "ok"
    assert "email_backend" in body["checks"]
    assert "celery_eager" in body["checks"]
