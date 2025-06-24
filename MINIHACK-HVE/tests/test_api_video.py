import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_generate_video(monkeypatch):
    # Mock AzureSoraService.create_video_job to avoid real API call
    class MockAzureSoraService:
        @staticmethod
        def create_video_job(prompt, duration, width=480, height=480):
            return {"id": "test-job-id", "status": "queued"}
    
    # Patch the service in the router
    import app.api.video as video_module
    video_module.AzureSoraService = MockAzureSoraService

    payload = {
        "prompt": "A cat playing piano in a jazz bar.",
        "duration": 5
    }
    response = client.post("/api/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == "test-job-id"
    assert data["status"] == "queued"
