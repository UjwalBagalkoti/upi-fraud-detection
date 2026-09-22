const BASE = import.meta.env.VITE_API_URL || ""; // "" = same-origin, correct for Vercel

async function request(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw data;
  return data;
}

export const checkTransaction = (body) => request("/api/transactions/check", { method: "POST", body });
export const getTransactions = (decision = "") =>
  request(`/api/transactions?limit=50${decision ? `&decision=${decision}` : ""}`);
export const getStats = () => request("/api/stats");
export const labelTransaction = (id, label) =>
  request(`/api/transactions/${id}/label`, { method: "PATCH", body: { label } });
export const addSamples = (n = 20) => request("/api/simulate", { method: "POST", body: { n } });
