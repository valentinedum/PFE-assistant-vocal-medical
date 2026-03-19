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
    with httpx.Client(base_url="http://localhost:8000", timeout=30.0) as client:
        params = {"text": "Je veux prendre un rendez-vous"}
        response = client.post("/predict", params=params)
        assert response.status_code == 200
        assert "response" in response.json()

def test_transcribe_audio_flow():
    audio_path = "tests/ressources/test_audio.wav"
    
    import os
    if not os.path.exists(audio_path):
        pytest.skip("Fichier audio de test manquant")

    with httpx.Client(base_url="http://localhost:8000", timeout=60.0) as client:
        files = {'file': ('test.wav', open(audio_path, 'rb'), 'audio/wav')}
        data = {'context': '{"step": "initial"}'}

        response = client.post("/transcribe", files=files, data=data, timeout=60.0)
        
        assert response.status_code == 200
        json_res = response.json()
        assert "response" in json_res