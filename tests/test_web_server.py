import pytest
from fastapi.testclient import TestClient
from hooky.web.server import app
from hooky.config import ENV_FILE

client = TestClient(app)

def test_index_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Hooky Studio" in response.text
    # Verify key controls are present
    assert "id=\"smart-recommendation-pill\"" in response.text
    assert "id=\"frame-mode-auto\"" in response.text
    assert "id=\"frame-mode-fit\"" in response.text
    assert "id=\"frame-mode-center\"" in response.text
    assert "id=\"tab-settings\"" in response.text
    assert "id=\"env-raw-textarea\"" in response.text

def test_doctor_endpoint():
    response = client.get("/api/doctor")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "checks" in data
    assert "gpu" in data

def test_channels_endpoint():
    response = client.get("/api/channels")
    assert response.status_code == 200
    data = response.json()
    assert "channels" in data

def test_outputs_endpoint():
    response = client.get("/api/outputs")
    assert response.status_code == 200
    data = response.json()
    assert "files" in data

def test_env_roundtrip():
    # Read current
    res = client.get("/api/env")
    assert res.status_code == 200
    initial = res.json()
    assert "raw" in initial
    assert "values" in initial

    # Test update with key-values
    test_key = "HOOKY_TEST_VAR"
    test_val = "verified_12345"
    payload = {"values": {test_key: test_val}}
    save_res = client.post("/api/env", json=payload)
    assert save_res.status_code == 200

    # Verify read back
    res2 = client.get("/api/env")
    assert res2.status_code == 200
    assert res2.json()["values"].get(test_key) == test_val

    # Clean up test var
    raw_clean = "\n".join([line for line in res2.json()["raw"].splitlines() if not line.startswith(test_key)])
    client.post("/api/env", json={"raw": raw_clean})

def test_render_aliases():
    # Test that route aliases exist and validate input
    res1 = client.post("/api/jobs/render_clip", json={"url": ""})
    # Should accept and launch job
    assert res1.status_code in (200, 400)
    
    res2 = client.post("/api/render", json={"url": "https://www.youtube.com/watch?v=EDCwQe7P8T0", "start": 10, "end": 20})
    assert res2.status_code == 200
    assert "job_id" in res2.json()
