# UPI Fraud Desk

Full-stack UPI fraud detection. Scores each payment with a **Random Forest + rule engine**, returns an
Allow / Review / Block decision with human-readable reasons, and learns from analyst reviews.

**Stack:** Flask · scikit-learn · SQLAlchemy (SQLite, or PostgreSQL via `DATABASE_URL`) · React + Vite

## Run it

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python train.py          # trains the model (~5 s), writes backend/model/
python app.py            # http://localhost:5000

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev              # http://localhost:5173  (proxies /api to :5000)
```

Tests:
```bash
cd backend && python -m pytest -q tests                      # 11 API tests
cd backend && python app.py &                                # UI tests need the API running
cd frontend && VITE_API_URL=http://localhost:5000 npm test   # 5 UI tests (jsdom)
```
Set `FLASK_DEBUG=1` for Flask's debugger/auto-reload (off by default).

## How scoring works

`risk = 0.65 × model probability + 0.35 × rule score`

| Risk | Decision |
|------|----------|
| ≥ 0.65 | BLOCK |
| 0.35 – 0.65 | REVIEW |
| < 0.35 | ALLOW |

- **Model** (`features.py`, `train.py`): amount, amount/balance, night hour, payment type, new device/payee, account age, payments in 24 h, location mismatch, round amount.
- **Rules** (`rules.py`): each rule adds weight and a plain-English reason shown in the UI.
- **Feedback loop**: marking a payment "Fraud" flags that payee ID; the next payment to it is blocked.

## API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/transactions/check` | Score + store a payment |
| GET | `/api/transactions?decision=BLOCK&limit=50` | List payments |
| PATCH | `/api/transactions/:id/label` | `{"label": "fraud" \| "legit" \| null}` |
| GET | `/api/stats` | Counts, blocked amount, model metrics |
| POST | `/api/simulate` | `{"n": 20}` demo payments |

## Next steps

- Replace `data_gen.py` with a real labelled dataset (e.g. PaySim-style) — keep the same columns or edit `features.py`.
- Retrain from analyst labels stored in `analyst_label`.
- Add auth (JWT), rate limiting, and SHAP explanations.
- Deploy: backend on Render/Railway with `DATABASE_URL`, frontend on Vercel with `VITE_API_URL`.

> The bundled metrics come from synthetic data and say nothing about real-world accuracy.
