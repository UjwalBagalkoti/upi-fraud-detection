import { useState } from "react";
import { checkTransaction } from "./api.js";
import { DECISION_MARK, DECISION_TEXT, money, pct, time } from "./format.js";

const BLANK = {
  receiver_vpa: "", amount: "", txn_type: "P2P", hour: new Date().getHours(), balance: 50000,
  account_age_days: 365, txns_24h: 1, new_device: false, new_payee: false, location_mismatch: false,
};

const PRESETS = {
  "Coffee at a shop": { receiver_vpa: "brewroom@ybl", amount: 180, txn_type: "P2M", hour: 9, balance: 24000,
    account_age_days: 900, txns_24h: 2, new_device: false, new_payee: false, location_mismatch: false },
  "Refund collect request": { receiver_vpa: "refund.desk@paytm", amount: 48000, txn_type: "COLLECT", hour: 2,
    balance: 50000, account_age_days: 12, txns_24h: 8, new_device: true, new_payee: true, location_mismatch: true },
};

export function CheckForm({ onResult }) {
  const [form, setForm] = useState(BLANK);
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setErrors({});
    try {
      onResult(await checkTransaction(form));
    } catch (err) {
      setErrors(err.fields || { _: err.error || "Could not reach the server. Is the backend running?" });
    } finally {
      setBusy(false);
    }
  };

  const field = (key, label, props = {}) => (
    <label className="field">
      <span>{label}</span>
      <input value={form[key]} onChange={(e) => set(key, e.target.value)} aria-invalid={!!errors[key]} {...props} />
      {errors[key] && <em className="err">{errors[key]}</em>}
    </label>
  );

  const check = (key, label) => (
    <label className="check">
      <input type="checkbox" checked={form[key]} onChange={(e) => set(key, e.target.checked)} />
      {label}
    </label>
  );

  return (
    <form className="panel" onSubmit={submit} noValidate>
      <h2>Check a payment</h2>
      <div className="presets">
        {Object.entries(PRESETS).map(([name, values]) => (
          <button type="button" key={name} className="link" onClick={() => { setForm(values); setErrors({}); }}>
            {name}
          </button>
        ))}
      </div>
      {field("receiver_vpa", "Payee UPI ID", { placeholder: "name@bank", autoComplete: "off" })}
      <div className="row">
        {field("amount", "Amount (₹)", { type: "number", min: 1, inputMode: "numeric" })}
        <label className="field">
          <span>Payment type</span>
          <select value={form.txn_type} onChange={(e) => set("txn_type", e.target.value)}>
            <option value="P2P">Person to person</option>
            <option value="P2M">Merchant</option>
            <option value="COLLECT">Collect request</option>
          </select>
        </label>
      </div>
      <div className="row three">
        {field("hour", "Hour (0–23)", { type: "number", min: 0, max: 23 })}
        {field("balance", "Balance (₹)", { type: "number", min: 0 })}
        {field("txns_24h", "Payments today", { type: "number", min: 0 })}
      </div>
      {field("account_age_days", "Account age (days)", { type: "number", min: 0 })}
      <div className="checks">
        {check("new_payee", "First payment to this payee")}
        {check("new_device", "Sent from a new device")}
        {check("location_mismatch", "Unusual location")}
      </div>
      {errors._ && <p className="err">{errors._}</p>}
      <button className="primary" disabled={busy}>{busy ? "Checking…" : "Check payment"}</button>
    </form>
  );
}

export function Gauge({ score, decision }) {
  return (
    <div className="gauge" role="img" aria-label={`Risk score ${pct(score)}, ${DECISION_TEXT[decision]}`}>
      <div className="zones">
        <i className="z allow" style={{ width: "35%" }} />
        <i className="z review" style={{ width: "30%" }} />
        <i className="z block" style={{ width: "35%" }} />
        <b className="marker" style={{ left: `${Math.min(score, 1) * 100}%` }} />
      </div>
      <div className="ticks"><span>Allow</span><span style={{ left: "35%" }}>Review</span><span style={{ left: "65%" }}>Block</span></div>
    </div>
  );
}

export function Result({ result }) {
  if (!result)
    return (
      <section className="panel result empty">
        <h2>Result</h2>
        <p>Check a payment to see its risk score and the reasons behind it.</p>
      </section>
    );
  const d = result.decision;
  return (
    <section className={`panel result ${d.toLowerCase()}`} aria-live="polite">
      <h2>Result</h2>
      <div className="verdict">
        <span className="score">{pct(result.risk_score)}</span>
        <span className="word">{DECISION_MARK[d]} {DECISION_TEXT[d]}</span>
      </div>
      <Gauge score={result.risk_score} decision={d} />
      <p className="meta">
        {money(result.amount)} to <b>{result.receiver_vpa}</b> · model {pct(result.ml_score)} · rules {pct(result.rule_score)}
      </p>
      <h3>Why</h3>
      {result.reasons.length ? (
        <ul className="reasons">{result.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
      ) : (
        <p className="meta">Nothing unusual about this payment.</p>
      )}
    </section>
  );
}

export function Stats({ stats, onSamples, busy }) {
  const s = stats;
  const items = s
    ? [
        ["Checked", s.total.toLocaleString("en-IN")],
        ["Allowed", s.allow.toLocaleString("en-IN")],
        ["In review", s.review.toLocaleString("en-IN")],
        ["Blocked", s.block.toLocaleString("en-IN")],
        ["Stopped", money(s.blocked_amount)],
      ]
    : [];
  return (
    <div className="stats">
      {items.map(([k, v]) => (
        <div key={k}><dd>{v}</dd><dt>{k}</dt></div>
      ))}
      <div className="grow">
        {s?.model && <small>Model: AUC {s.model.roc_auc} · recall {pct(s.model.recall)} · precision {pct(s.model.precision)} (synthetic data)</small>}
        <button className="link" onClick={onSamples} disabled={busy}>{busy ? "Adding…" : "Add 20 sample payments"}</button>
      </div>
    </div>
  );
}

export function Table({ rows, filter, onFilter, onLabel }) {
  return (
    <section className="panel table-wrap">
      <div className="table-head">
        <h2>Recent payments</h2>
        <label className="inline">
          Show
          <select value={filter} onChange={(e) => onFilter(e.target.value)}>
            <option value="">All</option>
            <option value="BLOCK">Blocked</option>
            <option value="REVIEW">In review</option>
            <option value="ALLOW">Allowed</option>
          </select>
        </label>
      </div>
      {rows.length === 0 ? (
        <p className="meta">No payments yet. Check one above or add sample payments.</p>
      ) : (
        <div className="scroll">
          <table>
            <thead>
              <tr><th>Time</th><th>Payee</th><th className="num">Amount</th><th>Type</th><th className="num">Risk</th><th>Decision</th><th>Main reason</th><th>Your review</th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{time(r.created_at)}</td>
                  <td className="vpa">{r.receiver_vpa}</td>
                  <td className="num">{money(r.amount)}</td>
                  <td>{r.txn_type}</td>
                  <td className="num">{pct(r.risk_score)}</td>
                  <td><span className={`pill ${r.decision.toLowerCase()}`}>{DECISION_MARK[r.decision]} {DECISION_TEXT[r.decision]}</span></td>
                  <td className="reason">{r.reasons[0] || "—"}</td>
                  <td>
                    {r.analyst_label ? (
                      <span>{r.analyst_label === "fraud" ? "Confirmed fraud" : "Marked safe"}{" "}
                        <button className="link" onClick={() => onLabel(r.id, null)}>Undo</button></span>
                    ) : (
                      <span className="actions">
                        <button className="link" onClick={() => onLabel(r.id, "fraud")}>Fraud</button>
                        <button className="link" onClick={() => onLabel(r.id, "legit")}>Safe</button>
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
