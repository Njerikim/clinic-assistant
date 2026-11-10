from fastapi.testclient import TestClient

from app.main import create_app


def test_home_page_loads_with_demo_keys():
    r = TestClient(create_app()).get("/")
    assert r.status_code == 200 and "Clinic assistant demo" in r.text
    assert "demo-key-clinic-a" in r.text


def test_home_page_never_exposes_real_keys():
    r = TestClient(create_app(keys={"s3cret-prod-key": "clinic_a"})).get("/")
    assert r.status_code == 200
    assert "s3cret-prod-key" not in r.text and "demo-key" not in r.text
