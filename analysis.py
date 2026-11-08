"""Recession and recovery in US jobs, 2006-2015.

Reads the BLS Current Employment Statistics extract (data/us-employment.csv,
public domain, seasonally adjusted, thousands of jobs) and writes
dashboard/data.json for the dashboard. Pure Python standard library.

Run:  python analysis.py
"""
import csv
import json
import os
from typing import Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))

SECTORS = {
    "mining_and_logging": "Mining & logging",
    "construction": "Construction",
    "manufacturing": "Manufacturing",
    "trade_transportation_utilties": "Trade, transport & utilities",
    "information": "Information",
    "financial_activities": "Financial activities",
    "professional_and_business_services": "Professional & business services",
    "education_and_health_services": "Education & health",
    "leisure_and_hospitality": "Leisure & hospitality",
    "other_services": "Other services",
    "government": "Government",
}


def load(path: str) -> List[Dict]:
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("no rows in %s" % path)
    out = []
    for r in rows:
        rec = {"month": r["month"][:7]}
        for k, v in r.items():
            if k != "month":
                rec[k] = float(v) if v not in ("", None) else None
        out.append(rec)
    out.sort(key=lambda r: r["month"])
    return out


def peak_trough(rows: List[Dict], col: str, peak_before: str = "2010-01") -> Dict:
    """Pre-recession peak (highest month before `peak_before`), the lowest
    month after it, and the first month the series got back to the peak."""
    before = [r for r in rows if r["month"] < peak_before and r[col] is not None]
    peak = max(before, key=lambda r: (r[col], r["month"]))
    after = [r for r in rows if r["month"] >= peak["month"] and r[col] is not None]
    trough = min(after, key=lambda r: (r[col], r["month"]))
    no_decline = trough["month"] == peak["month"]
    recovered: Optional[str] = peak["month"] if no_decline else next(
        (r["month"] for r in rows if r["month"] > trough["month"] and r[col] is not None and r[col] >= peak[col]), None)
    last = rows[-1]
    return {
        "peak_month": peak["month"], "peak": peak[col],
        "trough_month": trough["month"], "trough": trough[col],
        "loss": round(peak[col] - trough[col], 1),
        "drop_pct": round((trough[col] - peak[col]) / peak[col] * 100, 1),
        "recovered_month": recovered,
        "months_to_recover": months_between(trough["month"], recovered) if recovered else None,
        "end_vs_peak_pct": round((last[col] - peak[col]) / peak[col] * 100, 1),
        "no_decline": no_decline,
    }


def months_between(a: str, b: str) -> int:
    ya, ma = map(int, a.split("-"))
    yb, mb = map(int, b.split("-"))
    return (yb - ya) * 12 + (mb - ma)


def index_series(rows: List[Dict], col: str, base_month: str) -> List[float]:
    base = next(r[col] for r in rows if r["month"] == base_month)
    return [round(r[col] / base * 100, 2) for r in rows]


def build(rows: List[Dict]) -> Dict:
    total = peak_trough(rows, "nonfarm")
    sectors = []
    for col, label in SECTORS.items():
        pt = peak_trough(rows, col)
        pt.update({"key": col, "label": label, "index": index_series(rows, col, total["peak_month"]),
                   "share_start": round(rows[0][col] / rows[0]["nonfarm"] * 100, 1),
                   "share_end": round(rows[-1][col] / rows[-1]["nonfarm"] * 100, 1)})
        sectors.append(pt)
    sectors.sort(key=lambda s: s["drop_pct"])
    worst_month = min(rows, key=lambda r: r["nonfarm_change"] if r["nonfarm_change"] is not None else 0)
    return {
        "source": "U.S. Bureau of Labor Statistics, Current Employment Statistics (via vega-datasets). "
                  "Seasonally adjusted, thousands of jobs. Public domain.",
        "months": [r["month"] for r in rows],
        "nonfarm": [r["nonfarm"] for r in rows],
        "change": [r["nonfarm_change"] for r in rows],
        "total": total,
        "worst_month": {"month": worst_month["month"], "change": worst_month["nonfarm_change"]},
        "sectors": sectors,
    }


def main():
    rows = load(os.path.join(HERE, "data", "us-employment.csv"))
    out = build(rows)
    os.makedirs(os.path.join(HERE, "dashboard"), exist_ok=True)
    payload = json.dumps(out, separators=(",", ":"))
    with open(os.path.join(HERE, "dashboard", "data.json"), "w", encoding="utf-8") as fh:
        fh.write(payload)
    with open(os.path.join(HERE, "template.html"), encoding="utf-8") as fh:
        page = fh.read().replace("/*DATA*/null", payload.replace("</", "<\\/"))
    with open(os.path.join(HERE, "dashboard", "index.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    t = out["total"]
    print("Peak %s: %.0fk jobs. Trough %s: %.0fk (-%.0fk, %.1f%%). Back to peak: %s (%s months after trough)."
          % (t["peak_month"], t["peak"], t["trough_month"], t["trough"], t["loss"], t["drop_pct"],
             t["recovered_month"], t["months_to_recover"]))
    for s in out["sectors"]:
        print("  %-34s %6.1f%%  end vs peak %+5.1f%%  recovered %s" % (s["label"], s["drop_pct"], s["end_vs_peak_pct"], s["recovered_month"] or "no"))


if __name__ == "__main__":
    main()
