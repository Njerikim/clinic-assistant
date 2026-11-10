import json
import logging

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import create_app

A = {"X-API-Key": "demo-key-clinic-a"}
B = {"X-API-Key": "demo-key-clinic-b"}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def ask(client, headers, q):
    return client.post("/ask", json={"question": q}, headers=headers)


def test_missing_or_wrong_key_is_rejected(client):
    assert client.post("/ask", json={"question": "opening hours?"}).status_code == 401
    assert ask(client, {"X-API-Key": "nope"}, "opening hours?").status_code == 401


def test_client_cannot_name_a_tenant(client):
    r = client.post("/ask", json={"question": "opening hours?", "tenant": "clinic_b"}, headers=A)
    assert r.status_code == 422


def test_each_clinic_gets_its_own_answer_to_the_same_question(client):
    ra = ask(client, A, "What time do you open on Saturday?").json()
    rb = ask(client, B, "What time do you open on Saturday?").json()
    assert ra["sources"][0]["id"].startswith("a")
    assert rb["sources"][0]["id"].startswith("b")
    assert ra["answer"] != rb["answer"]


def test_cache_does_not_leak_across_tenants(client):
    q = "How do I book an appointment?"
    first = ask(client, A, q).json()
    second = ask(client, B, q).json()  # same text, warm cache for A
    assert first["sources"][0]["id"].startswith("a")
    assert second["sources"][0]["id"].startswith("b")


def test_index_files_share_no_documents():
    from app.store import IndexStore

    store = IndexStore.load(config.data_dir())
    assert store.doc_ids("clinic_a").isdisjoint(store.doc_ids("clinic_b"))
    with pytest.raises(KeyError):
        store.search("clinic_c", "anything")


B_DOCS = json.loads((config.data_dir() / "clinic_b.json").read_text(encoding="utf-8"))
A_DOCS = json.loads((config.data_dir() / "clinic_a.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("doc", B_DOCS, ids=lambda d: d["id"])
def test_clinic_a_never_receives_clinic_b_documents(client, doc):
    body = ask(client, A, doc["en"]).json()
    assert all(not s["id"].startswith("b") for s in body["sources"])
    assert doc["en"] not in body["answer"]


@pytest.mark.parametrize("doc", A_DOCS, ids=lambda d: d["id"])
def test_clinic_b_never_receives_clinic_a_documents(client, doc):
    body = ask(client, B, doc["en"]).json()
    assert all(not s["id"].startswith("a") for s in body["sources"])
    assert doc["en"] not in body["answer"]


def test_logs_do_not_contain_phone_numbers_or_ids(client, caplog):
    with caplog.at_level(logging.INFO, logger="clinic_assistant"):
        ask(client, A, "Please call me on 0712 345 678 or email jane@example.com, ID 12345678")
    assert "0712" not in caplog.text and "jane@example.com" not in caplog.text and "12345678" not in caplog.text
    assert "[phone]" in caplog.text
