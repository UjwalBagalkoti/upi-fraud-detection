"""Combines the ML model and the rule engine into one risk score + decision."""
import json
import os
from functools import lru_cache

import joblib

from features import vectorize
from rules import rule_score

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
ML_WEIGHT = 0.65
BLOCK_AT, REVIEW_AT = 0.65, 0.35


@lru_cache(maxsize=1)
def _model():
    path = os.path.join(MODEL_DIR, "model.joblib")
    if not os.path.exists(path):
        raise RuntimeError("Model not found. Run `python train.py` first.")
    return joblib.load(path)


def load_metrics():
    path = os.path.join(MODEL_DIR, "metrics.json")
    if not os.path.exists(path):
        return None
    with open(path) as fh:
        return json.load(fh)


def decide(risk):
    return "BLOCK" if risk >= BLOCK_AT else "REVIEW" if risk >= REVIEW_AT else "ALLOW"


def score_transaction(t):
    ml = float(_model().predict_proba(vectorize([t]))[0][1])
    rules, reasons = rule_score(t)
    risk = ML_WEIGHT * ml + (1 - ML_WEIGHT) * rules
    if t.get("flagged_payee"):
        risk = max(risk, 0.9)
    if ml >= 0.5 and len(reasons) < 2:
        reasons.append("Pattern closely matches known fraud cases")
    return {
        "ml_score": round(ml, 4),
        "rule_score": round(rules, 4),
        "risk_score": round(risk, 4),
        "decision": decide(risk),
        "reasons": reasons,
    }
