import pytest
from fastapi.testclient import TestClient
from hooky.web.server import app, get_web_token
from hooky.config import ENV_FILE

TOKEN = get_web_token()
client = TestClient(app, headers={"X-Hooky-Token": TOKEN})
unauthed_client = TestClient(app)


def test_index_endpoint():
    response = unauthed_client.get("/")
    assert response.status_code == 200
    assert "Hooky Studio" in response.text
    # Verify auth token was injected into HTML
    assert TOKEN in response.text
    # Verify key controls are present
    assert 'id="smart-recommendation-pill"' in response.text
    assert 'id="frame-mode-auto"' in response.text
    assert 'id="frame-mode-fit"' in response.text
    assert 'id="frame-mode-center"' in response.text
    assert 'id="tab-settings"' in response.text
    assert 'id="env-raw-textarea"' in response.text


def test_token_auth_enforcement():
    # Without token -> 401
    res = unauthed_client.get("/api/doctor")
    assert res.status_code == 401
    assert "Unauthorized" in res.json().get("detail", "")

    # With invalid token -> 401
    bad_res = unauthed_client.get("/api/doctor", headers={"X-Hooky-Token": "invalid_bad_token"})
    assert bad_res.status_code == 401

    # With valid token query param -> 200
    query_res = unauthed_client.get(f"/api/doctor?token={TOKEN}")
    assert query_res.status_code == 200

    # With valid token header -> 200
    good_res = client.get("/api/doctor")
    assert good_res.status_code == 200


def test_host_header_validation():
    # Loopback hosts -> allowed
    res_local = client.get("/api/doctor", headers={"Host": "127.0.0.1:8000"})
    assert res_local.status_code == 200

    # Forbidden external host -> 403
    res_bad_host = client.get("/api/doctor", headers={"Host": "evil.example.com"})
    assert res_bad_host.status_code == 403


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
    res = client.get("/api/env")
    assert res.status_code == 200
    initial = res.json()
    assert "raw" in initial
    assert "values" in initial

    test_key = "HOOKY_TEST_VAR"
    test_val = "verified_12345"
    payload = {"values": {test_key: test_val}}
    save_res = client.post("/api/env", json=payload)
    assert save_res.status_code == 200

    res2 = client.get("/api/env")
    assert res2.status_code == 200
    assert res2.json()["values"].get(test_key) == test_val

    raw_clean = "\n".join([line for line in res2.json()["raw"].splitlines() if not line.startswith(test_key)])
    client.post("/api/env", json={"raw": raw_clean})


def test_render_validation():
    # Empty url -> 400
    res1 = client.post("/api/jobs/render_clip", json={"url": ""})
    assert res1.status_code == 400

    # Malicious or flag url -> 400
    res_flag = client.post("/api/jobs/render_clip", json={"url": "--exec rm -rf /"})
    assert res_flag.status_code == 400

    # Invalid timestamps: end <= start -> 400
    res_time = client.post("/api/jobs/render_clip", json={
        "url": "https://www.youtube.com/watch?v=EDCwQe7P8T0",
        "start": 50,
        "end": 20,
    })
    assert res_time.status_code == 400

    # Valid render job -> 200
    res_ok = client.post("/api/render", json={
        "url": "https://www.youtube.com/watch?v=EDCwQe7P8T0",
        "start": 10,
        "end": 20,
    })
    assert res_ok.status_code == 200
    assert "job_id" in res_ok.json()


def test_make_target_validation():
    # Injection attempt in target with leading '-' -> 400
    res_bad = client.post("/api/make", json={"target": "--custom-malicious-arg"})
    assert res_bad.status_code == 400


def test_cors_and_password_masking():
    # 1. Foreign origin should not receive Access-Control-Allow-Origin
    res_cors = client.get("/api/env", headers={"Origin": "http://evil.example"})
    assert res_cors.headers.get("access-control-allow-origin") is None or res_cors.headers.get("access-control-allow-origin") != "http://evil.example"

    # 2. Local origin should be accepted
    res_local = client.get("/api/env", headers={"Origin": "http://localhost:8000"})
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:8000"

    # 3. Simple text/plain post without json content-type must be rejected with 415
    res_bad_ct = client.post("/api/env", content="RAW_TEST=1", headers={"Content-Type": "text/plain"})
    assert res_bad_ct.status_code == 415

    # 4. Sensitive credentials masking verification
    res_env = client.get("/api/env")
    assert res_env.status_code == 200
    values = res_env.json().get("values", {})
    if "IG_PASSWORD" in values and values["IG_PASSWORD"]:
        assert values["IG_PASSWORD"] == "••••••••"
    if "GEMINI_API_KEY" in values and values["GEMINI_API_KEY"]:
        assert values["GEMINI_API_KEY"] == "••••••••"
