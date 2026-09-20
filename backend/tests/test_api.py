import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app import create_app  # noqa: E402
from scoring import MODEL_DIR  # noqa: E402

if not os.path.exists(os.path.join(MODEL_DIR, "model.joblib")):
    import train
    train.main()

SAFE = {"receiver_vpa": "shop@ybl", "amount": 250, "txn_type": "P2M", "hour": 14,
        "balance": 20000, "account_age_days": 900, "txns_24h": 2}
RISKY = {"receiver_vpa": "refund.helpdesk@paytm", "amount": 48000, "txn_type": "COLLECT", "hour": 2,
         "balance": 50000, "account_age_days": 12, "txns_24h": 8,
         "new_device": True, "new_payee": True, "location_mismatch": True}


@pytest.fixture()
def client():
    app = create_app({"SQLALCHEMY_DATABASE_URI": "sqlite://", "TESTING": True})
    return app.test_client()


def test_safe_payment_is_allowed(client):
    r = client.post("/api/transactions/check", json=SAFE)
    assert r.status_code == 201 and r.json["decision"] == "ALLOW"


def test_risky_collect_is_blocked_with_reasons(client):
    r = client.post("/api/transactions/check", json=RISKY)
    assert r.json["decision"] == "BLOCK"
    assert len(r.json["reasons"]) >= 3


def test_validation_errors(client):
    r = client.post("/api/transactions/check", json={"receiver_vpa": "nope", "amount": -5})
    assert r.status_code == 400 and {"receiver_vpa", "amount"} <= set(r.json["fields"])


def test_confirmed_fraud_payee_gets_flagged_next_time(client):
    first = client.post("/api/transactions/check", json={**SAFE, "receiver_vpa": "scam@ybl"}).json
    client.patch(f"/api/transactions/{first['id']}/label", json={"label": "fraud"})
    again = client.post("/api/transactions/check", json={**SAFE, "receiver_vpa": "scam@ybl"}).json
    assert again["decision"] == "BLOCK"


def test_stats_and_simulate(client):
    client.post("/api/simulate", json={"n": 15})
    s = client.get("/api/stats").json
    assert s["total"] == 15 and s["allow"] + s["review"] + s["block"] == 15
    assert len(client.get("/api/transactions?limit=5").json) == 5


@pytest.mark.parametrize("body", ["[1]", '"text"', "not json", "null"])
def test_non_object_bodies_return_400_not_500(client, body):
    h = {"Content-Type": "application/json"}
    assert client.post("/api/transactions/check", data=body, headers=h).status_code == 400
    assert client.post("/api/simulate", data=body, headers=h).status_code in (201, 400)
    first = client.post("/api/transactions/check", json=SAFE).json
    assert client.patch(f"/api/transactions/{first['id']}/label", data=body, headers=h).status_code in (200, 400)


def test_simulate_rejects_bad_n_and_caps_large_n(client):
    assert client.post("/api/simulate", json={"n": "abc"}).status_code == 400
    assert client.post("/api/simulate", json={"n": 5000}).json["created"] == 100


def test_list_limit_is_clamped(client):
    client.post("/api/transactions/check", json=SAFE)
    assert client.get("/api/transactions?limit=-5").status_code == 200
    assert len(client.get("/api/transactions?limit=-5").json) == 1
