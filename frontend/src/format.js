const inr = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 });
export const money = (n) => inr.format(n);
export const pct = (n) => `${Math.round(n * 100)}%`;
export const time = (iso) =>
  new Date(iso).toLocaleString("en-IN", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

export const DECISION_TEXT = { ALLOW: "Allow", REVIEW: "Review", BLOCK: "Block" };
// Shape + text carry the meaning, colour only reinforces it.
export const DECISION_MARK = { ALLOW: "●", REVIEW: "◆", BLOCK: "■" };
