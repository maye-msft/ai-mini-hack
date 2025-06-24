import requests
import pytest
import time

def test_generate_video_integration():
    url = "http://localhost:8080/api/generate"
    payload = {
        "prompt": "A cat playing piano in a jazz bar.",
        "duration": 5
    }
    response = requests.post(url, json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "job_id" in data
    job_id = data["job_id"]
    assert data["status"] in ("queued", "processing", "succeeded")

    # Poll status endpoint until succeeded or failed
    status_url = f"http://localhost:8080/api/status/{job_id}"
    status = None
    video_url = None
    for _ in range(20):  # up to 100 seconds
        status_resp = requests.get(status_url)
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        status = status_data["status"]
        if status == "succeeded":
            video_url = status_data.get("video_url")
            break
        elif status == "failed":
            pytest.fail("Video generation failed")
        time.sleep(5)
    assert status == "succeeded"
    assert video_url, "No video_url returned on success"

    # Download the video
    video_resp = requests.get(f"http://localhost:8080{video_url}")
    assert video_resp.status_code == 200
    assert video_resp.headers["content-type"].startswith("video/") or video_resp.headers["content-type"] == "application/octet-stream"
    assert len(video_resp.content) > 0
