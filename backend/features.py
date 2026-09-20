"""Turns raw transaction dicts into the numeric features the model uses."""
import numpy as np
import pandas as pd

TXN_TYPES = ["P2P", "P2M", "COLLECT"]

FEATURES = [
    "log_amount", "amount_to_balance", "is_night", "is_collect", "is_p2m",
    "new_device", "new_payee", "account_age_days", "txns_24h",
    "location_mismatch", "round_amount",
]


def vectorize(records):
    """records: list[dict] or DataFrame with raw transaction fields -> DataFrame[FEATURES]."""
    df = pd.DataFrame(records)
    out = pd.DataFrame(index=df.index)
    amount = df["amount"].astype(float)
    out["log_amount"] = np.log1p(amount)
    out["amount_to_balance"] = (amount / df["balance"].astype(float).clip(lower=1)).clip(upper=1)
    out["is_night"] = (df["hour"] <= 4).astype(int)
    out["is_collect"] = (df["txn_type"] == "COLLECT").astype(int)
    out["is_p2m"] = (df["txn_type"] == "P2M").astype(int)
    out["new_device"] = df["new_device"].astype(int)
    out["new_payee"] = df["new_payee"].astype(int)
    out["account_age_days"] = df["account_age_days"].astype(float)
    out["txns_24h"] = df["txns_24h"].astype(float)
    out["location_mismatch"] = df["location_mismatch"].astype(int)
    out["round_amount"] = ((amount % 1000 == 0) & (amount >= 5000)).astype(int)
    return out[FEATURES]
