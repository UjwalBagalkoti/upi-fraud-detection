"""Transparent rule engine. Gives a 0-1 score and human-readable reasons."""


def rule_score(t):
    score, reasons = 0.0, []

    def hit(weight, msg):
        nonlocal score
        score += weight
        reasons.append(msg)

    amt = t["amount"]
    ratio = amt / max(t["balance"], 1)

    if t.get("flagged_payee"):
        hit(0.50, "Payee was confirmed as fraud in an earlier review")
    if t["txn_type"] == "COLLECT" and amt >= 5000:
        hit(0.30, "Collect request for a large amount")
    if t["new_payee"] and amt >= 10000:
        hit(0.25, "Large payment to a first-time payee")
    if t["new_device"] and amt >= 5000:
        hit(0.20, "High amount from a new device")
    if ratio >= 0.9 and amt >= 5000:
        hit(0.20, "Uses over 90% of the account balance")
    if t["account_age_days"] < 30 and amt >= 5000:
        hit(0.15, "New account moving a large amount")
    if t["txns_24h"] >= 10:
        hit(0.15, "Unusually many transactions in the last 24 hours")
    if t["hour"] <= 4:
        hit(0.10, "Made between 12 AM and 5 AM")
    if t["location_mismatch"]:
        hit(0.10, "Location differs from the usual one")
    if amt >= 100000:
        hit(0.10, "At or above the ₹1 lakh UPI limit")

    return min(score, 1.0), reasons
