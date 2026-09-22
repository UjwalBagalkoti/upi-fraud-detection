import json
import os
from datetime import datetime, timedelta, timezone

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from data_gen import simulate
from features import TXN_TYPES
from scoring import load_metrics, score_transaction

db = SQLAlchemy()

INPUT_FIELDS = [
    "sender_vpa", "receiver_vpa", "amount", "txn_type", "hour", "balance",
    "account_age_days", "txns_24h", "new_device", "new_payee", "location_mismatch",
]


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=_now, index=True)
    sender_vpa = db.Column(db.String(80))
    receiver_vpa = db.Column(db.String(80), index=True)
    amount = db.Column(db.Float)
    txn_type = db.Column(db.String(10))
    hour = db.Column(db.Integer)
    balance = db.Column(db.Float)
    account_age_days = db.Column(db.Float)
    txns_24h = db.Column(db.Integer)
    new_device = db.Column(db.Boolean)
    new_payee = db.Column(db.Boolean)
    location_mismatch = db.Column(db.Boolean)
    ml_score = db.Column(db.Float)
    rule_score = db.Column(db.Float)
    risk_score = db.Column(db.Float)
    decision = db.Column(db.String(10), index=True)
    reasons = db.Column(db.Text)
    analyst_label = db.Column(db.String(10))  # "fraud" | "legit" | None

    def to_dict(self):
        d = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        d["created_at"] = self.created_at.isoformat() + "Z"
        d["reasons"] = json.loads(self.reasons or "[]")
        return d


def json_body():
    """Request JSON as a dict; anything else (bad JSON, list, string) becomes {}."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _as_bool(v):
    return v if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")


def parse_txn(d):
    """Validate a request body. Returns (transaction dict, None) or (None, {field: message})."""
    errors = {}

    def num(key, lo, hi, default=None):
        v = d.get(key, default)
        if v is None or v == "":
            errors[key] = "Required"
            return None
        try:
            v = float(v)
        except (TypeError, ValueError):
            errors[key] = "Enter a number"
            return None
        if not lo <= v <= hi:
            errors[key] = f"Must be between {lo:g} and {hi:g}"
            return None
        return v

    t = {
        "sender_vpa": str(d.get("sender_vpa") or "you@upi").strip().lower()[:80],
        "receiver_vpa": str(d.get("receiver_vpa") or "").strip().lower()[:80],
        "amount": num("amount", 1, 1_000_000),
        "hour": num("hour", 0, 23, datetime.now().hour),
        "balance": num("balance", 0, 1e9, 50000),
        "account_age_days": num("account_age_days", 0, 36500, 365),
        "txns_24h": num("txns_24h", 0, 1000, 1),
        "txn_type": str(d.get("txn_type") or "P2P").upper(),
        "new_device": _as_bool(d.get("new_device", False)),
        "new_payee": _as_bool(d.get("new_payee", False)),
        "location_mismatch": _as_bool(d.get("location_mismatch", False)),
    }
    if "@" not in t["receiver_vpa"] or t["receiver_vpa"].startswith("@"):
        errors["receiver_vpa"] = "Enter a UPI ID like name@bank"
    if t["txn_type"] not in TXN_TYPES:
        errors["txn_type"] = f"Must be one of {', '.join(TXN_TYPES)}"
    if errors:
        return None, errors
    t["hour"], t["txns_24h"] = int(t["hour"]), int(t["txns_24h"])
    return t, None


def score_and_save(t, created_at=None):
    t["flagged_payee"] = db.session.query(Transaction.id).filter_by(
        receiver_vpa=t["receiver_vpa"], analyst_label="fraud").first() is not None
    result = score_transaction(t)
    row = Transaction(
        **{k: t[k] for k in INPUT_FIELDS},
        ml_score=result["ml_score"], rule_score=result["rule_score"],
        risk_score=result["risk_score"], decision=result["decision"],
        reasons=json.dumps(result["reasons"]),
    )
    if created_at:
        row.created_at = created_at
    db.session.add(row)
    return row


def create_app(config=None):
    app = Flask(__name__)
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        if os.getenv("VERCEL"):
            raise RuntimeError("DATABASE_URL is required on Vercel (SQLite doesn't persist there). Add a Postgres integration and set the env var.")
        db_url = "sqlite:///upi_fraud.db"
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config.update(config or {})
    CORS(app, origins=os.getenv("CORS_ORIGINS", "*").split(","))
    db.init_app(app)
    with app.app_context():
        db.create_all()

    @app.get("/api/health")
    def health():
        return jsonify(status="ok", model=load_metrics() is not None)

    @app.post("/api/transactions/check")
    def check():
        t, errors = parse_txn(json_body())
        if errors:
            return jsonify(error="Invalid transaction", fields=errors), 400
        row = score_and_save(t)
        db.session.commit()
        return jsonify(row.to_dict()), 201

    @app.get("/api/transactions")
    def list_transactions():
        q = Transaction.query
        decision = request.args.get("decision", "").upper()
        if decision in ("ALLOW", "REVIEW", "BLOCK"):
            q = q.filter_by(decision=decision)
        limit = min(max(request.args.get("limit", 50, type=int), 1), 200)
        rows = q.order_by(Transaction.created_at.desc(), Transaction.id.desc()).limit(limit).all()
        return jsonify([r.to_dict() for r in rows])

    @app.patch("/api/transactions/<int:txn_id>/label")
    def label(txn_id):
        row = db.get_or_404(Transaction, txn_id)
        value = json_body().get("label")
        if value not in ("fraud", "legit", None):
            return jsonify(error="label must be 'fraud' or 'legit'"), 400
        row.analyst_label = value
        db.session.commit()
        return jsonify(row.to_dict())

    @app.get("/api/stats")
    def stats():
        counts = dict(db.session.query(Transaction.decision, func.count()).group_by(Transaction.decision).all())
        blocked_amount = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter_by(decision="BLOCK").scalar()
        avg_risk = db.session.query(func.coalesce(func.avg(Transaction.risk_score), 0)).scalar()
        total = sum(counts.values())
        return jsonify(
            total=total,
            allow=counts.get("ALLOW", 0), review=counts.get("REVIEW", 0), block=counts.get("BLOCK", 0),
            blocked_amount=blocked_amount, avg_risk=round(avg_risk, 4),
            confirmed_fraud=Transaction.query.filter_by(analyst_label="fraud").count(),
            model=load_metrics(),
        )

    @app.post("/api/simulate")
    def simulate_route():
        try:
            n = int(json_body().get("n", 20))
        except (TypeError, ValueError):
            return jsonify(error="n must be a whole number"), 400
        n = min(max(n, 1), 100)
        now = _now()
        rows = simulate(n)
        for i, t in enumerate(rows):
            score_and_save(t, created_at=now - timedelta(minutes=3 * i))
        db.session.commit()
        return jsonify(created=len(rows)), 201

    return app


if __name__ == "__main__":
    create_app().run(port=int(os.getenv("PORT", 5000)), debug=os.getenv("FLASK_DEBUG") == "1")
