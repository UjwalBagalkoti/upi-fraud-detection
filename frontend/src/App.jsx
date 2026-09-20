import { useCallback, useEffect, useState } from "react";
import { addSamples, getStats, getTransactions, labelTransaction } from "./api.js";
import { CheckForm, Result, Stats, Table } from "./components.jsx";

export default function App() {
  const [result, setResult] = useState(null);
  const [stats, setStats] = useState(null);
  const [rows, setRows] = useState([]);
  const [filter, setFilter] = useState("");
  const [busy, setBusy] = useState(false);
  const [offline, setOffline] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const [s, t] = await Promise.all([getStats(), getTransactions(filter)]);
      setStats(s);
      setRows(t);
      setOffline(false);
    } catch {
      setOffline(true);
    }
  }, [filter]);

  useEffect(() => { refresh(); }, [refresh]);

  const onResult = (r) => { setResult(r); refresh(); };
  const onSamples = async () => { setBusy(true); try { await addSamples(20); await refresh(); } finally { setBusy(false); } };
  const onLabel = async (id, label) => { await labelTransaction(id, label); refresh(); };

  return (
    <main>
      <header>
        <h1>UPI Fraud Desk</h1>
        <p>Score payments, see why they were flagged, and teach the system from your reviews.</p>
      </header>
      {offline && <p className="banner">Can’t reach the backend. Start it with <code>python app.py</code> in <code>backend/</code>.</p>}
      <Stats stats={stats} onSamples={onSamples} busy={busy} />
      <div className="grid">
        <CheckForm onResult={onResult} />
        <Result result={result} />
      </div>
      <Table rows={rows} filter={filter} onFilter={setFilter} onLabel={onLabel} />
    </main>
  );
}
