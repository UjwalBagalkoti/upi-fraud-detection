"""Train the fraud model:  python train.py"""
import json
import os

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import average_precision_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import train_test_split

from data_gen import generate
from features import FEATURES, vectorize

MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")


def main():
    df = generate()
    X, y = vectorize(df), df["is_fraud"]
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)

    model = RandomForestClassifier(
        n_estimators=200, min_samples_leaf=3, class_weight="balanced_subsample",
        n_jobs=-1, random_state=42,
    ).fit(X_tr, y_tr)

    proba = model.predict_proba(X_te)[:, 1]
    p, r, f1, _ = precision_recall_fscore_support(y_te, proba >= 0.5, average="binary", zero_division=0)
    metrics = {
        "roc_auc": round(roc_auc_score(y_te, proba), 4),
        "avg_precision": round(average_precision_score(y_te, proba), 4),
        "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
        "train_rows": int(len(X_tr)), "test_rows": int(len(X_te)),
        "fraud_rate": round(float(y.mean()), 4),
        "feature_importance": {k: round(float(v), 4) for k, v in
                               sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])},
    }
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "model.joblib"))
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w") as fh:
        json.dump(metrics, fh, indent=2)
    print(json.dumps({k: v for k, v in metrics.items() if k != "feature_importance"}, indent=2))
    return metrics


if __name__ == "__main__":
    main()
