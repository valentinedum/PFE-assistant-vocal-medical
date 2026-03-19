import httpx
import pytest

def test_health_check():
    with httpx.Client(base_url="http://localhost:8000") as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

def test_prometheus_metrics():
    with httpx.Client(base_url="http://localhost:8000") as client:
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "api_requests_total" in response.text

def test_predict_intent_flow():
    with httpx.Client(base_url="http://localhost:8000", timeout=180.0) as client:
        params = {"text": "Je veux prendre un rendez-vous"}
        response = client.post("/predict", params=params)
        assert response.status_code == 200
        assert "response" in response.json()
