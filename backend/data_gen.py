"""Synthetic UPI transaction generator (training data + demo simulator).

Swap this for a real labelled dataset when you have one - just keep the same columns.
"""
import numpy as np
import pandas as pd

RAW_COLUMNS = [
    "amount", "hour", "txn_type", "balance", "account_age_days",
    "txns_24h", "new_device", "new_payee", "location_mismatch",
]
BANKS = ["okhdfcbank", "oksbi", "okicici", "ybl", "paytm", "axl", "ibl"]
NAMES = ["ravi", "meena", "arjun", "priya", "kiran", "sneha", "vikram", "anita",
         "rahul", "divya", "suresh", "lakshmi", "manoj", "pooja", "deepak", "nisha"]


def generate(n=30000, fraud_rate=0.04, seed=42):
    rng = np.random.default_rng(seed)
    fraud = rng.random(n) < fraud_rate
    f, l = fraud, ~fraud
    nf, nl = f.sum(), l.sum()

    amount = np.zeros(n)
    amount[l] = rng.lognormal(6.2, 1.1, nl)
    amount[f] = rng.lognormal(8.4, 1.2, nf)
    amount = np.clip(np.round(amount), 1, 100000)
    # scammers like round numbers
    rounded = f & (rng.random(n) < 0.35)
    amount[rounded] = np.clip(np.round(amount[rounded], -3), 1000, 100000)

    stealth = f & (rng.random(n) < 0.20)  # low-and-slow fraud that mimics normal behaviour
    amount[stealth] = np.clip(np.round(rng.lognormal(6.3, 1.0, stealth.sum())), 1, 100000)

    day_w = np.array([1, 1, 1, 1, 1, 2, 4, 6, 7, 7, 7, 7, 7, 7, 7, 7, 7, 8, 8, 8, 7, 5, 3, 2], float)
    hour = np.zeros(n, int)
    hour[l] = rng.choice(24, nl, p=day_w / day_w.sum())
    night = rng.random(nf) < 0.45
    hour[f] = np.where(night, rng.integers(0, 5, nf), rng.integers(5, 24, nf))

    txn_type = np.empty(n, object)
    txn_type[l] = rng.choice(["P2P", "P2M", "COLLECT"], nl, p=[0.55, 0.42, 0.03])
    txn_type[f] = rng.choice(["P2P", "P2M", "COLLECT"], nf, p=[0.45, 0.10, 0.45])

    balance = np.zeros(n)
    balance[l] = amount[l] * rng.uniform(1.1, 80, nl)
    balance[f] = amount[f] * rng.uniform(1.0, 2.0, nf)

    age = np.zeros(n)
    age[l] = rng.lognormal(6.0, 1.0, nl)
    young = rng.random(nf) < 0.4
    age[f] = np.where(young, rng.uniform(1, 30, nf), rng.lognormal(5.5, 1.0, nf))

    txns = np.zeros(n)
    txns[l] = rng.poisson(2, nl)
    txns[f] = rng.poisson(6, nf)

    def flag(p_legit, p_fraud):
        x = np.zeros(n, int)
        x[l] = rng.random(nl) < p_legit
        x[f] = rng.random(nf) < p_fraud
        return x

    new_device_, new_payee_, loc_ = flag(0.03, 0.35), flag(0.25, 0.80), flag(0.04, 0.30)
    for arr, p in ((new_device_, 0.03), (new_payee_, 0.25), (loc_, 0.04)):
        arr[stealth] = (rng.random(stealth.sum()) < p).astype(int)
    txn_type[stealth] = rng.choice(["P2P", "P2M"], stealth.sum(), p=[0.6, 0.4])
    hour[stealth] = rng.choice(24, stealth.sum(), p=day_w / day_w.sum())
    balance[stealth] = amount[stealth] * rng.uniform(1.1, 80, stealth.sum())

    return pd.DataFrame({
        "amount": amount,
        "hour": hour,
        "txn_type": txn_type,
        "balance": np.round(balance),
        "account_age_days": np.round(age),
        "txns_24h": txns.astype(int),
        "new_device": new_device_,
        "new_payee": new_payee_,
        "location_mismatch": loc_,
        "is_fraud": fraud.astype(int),
    })


def _vpa(rng):
    return f"{rng.choice(NAMES)}{rng.integers(10, 99)}@{rng.choice(BANKS)}"


def simulate(n=20, fraud_rate=0.25, seed=None):
    """Return n demo transactions (list of dicts) with sender/receiver VPAs."""
    rng = np.random.default_rng(seed)
    df = generate(n, fraud_rate, seed=int(rng.integers(0, 2**31)))
    rows = df.drop(columns="is_fraud").to_dict("records")
    for r in rows:
        r["sender_vpa"], r["receiver_vpa"] = _vpa(rng), _vpa(rng)
        for k in ("new_device", "new_payee", "location_mismatch"):
            r[k] = bool(r[k])
        for k in ("hour", "txns_24h"):
            r[k] = int(r[k])
        r["amount"], r["balance"], r["account_age_days"] = float(r["amount"]), float(r["balance"]), float(r["account_age_days"])
    return rows
