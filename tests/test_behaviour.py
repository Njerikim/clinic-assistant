import pytest
from fastapi.testclient import TestClient

from app.guards import needs_handover
from app.main import create_app

A = {"X-API-Key": "demo-key-clinic-a"}
client = TestClient(create_app())


@pytest.mark.parametrize("q", [
    "What dose of paracetamol should I give my child?",
    "Naweza kunywa dawa gani kwa maumivu ya kichwa?",
    "Dozi ya antibiotics kwa mtoto ni ngapi?",
])
def test_medicine_questions_are_handed_over(q):
    assert needs_handover(q)
    r = client.post("/ask", json={"question": q}, headers=A).json()
    assert r["status"] == "handover" and r["sources"] == []


def test_admin_pharmacy_question_is_not_a_handover():
    assert not needs_handover("What time does the pharmacy open?")


def test_gibberish_gets_no_answer_not_a_guess():
    r = client.post("/ask", json={"question": "zzzz qqqq xxxx"}, headers=A).json()
    assert r["status"] == "no_answer"


def test_swahili_question_gets_swahili_answer():
    r = client.post("/ask", json={"question": "Mnafungua saa ngapi Jumamosi?"}, headers=A).json()
    assert r["status"] == "answered" and "Jumamosi" in r["answer"]


def test_health_reports_index_version():
    assert client.get("/health").json()["index_version"] == "v1"
