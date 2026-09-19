#!/usr/bin/env python3
"""Estimated time saved by each of the top three allocations versus the current one (paired simulated days).

Re-runs the model at demand x1.0, x0.7 and x1.3; for every allocation the 3-day rotation is re-optimised at that demand
(as it is for the current allocation), then all are evaluated on the same 3,000 untouched simulated days.
"""
import csv, io, contextlib, runpy, sys
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
WORKDAYS_PER_YEAR = 250
top = list(csv.DictReader(open(DATA / "top3_allocations.csv", encoding="utf-8")))
out_rows = []
for cs in (1.0, 0.7, 1.3):
    sys.argv = ["optimize_runs.py", "--scenario", "none", "--cscale", str(cs), "--days", "900", "--val-days", "300", "--passes", "8"]
    with contextlib.redirect_stdout(io.StringIO()):
        g = runpy.run_path(str(BASE / "scripts" / "optimize_runs.py"), run_name="__main__")
    RUNS, nodes, n, train, Sim, local_search = g["RUNS"], g["nodes"], g["n"], g["train"], g["Sim"], g["local_search"]
    test = Sim(3000, seed=123); CAP = g["CAP"]
    idx = {nd["name"]: i for i, nd in enumerate(nodes)}

    def evaluate(alloc, cls):
        test.load(alloc, cls)
        T = [np.array(test.T[r]) for r in range(3)]
        return T, [np.maximum(t - CAP, 0) for t in T]
    Tb, Ob = evaluate(g["base_alloc"], g["base_cls"])
    tot_b = sum(Tb); over_b = sum(Ob)
    print(f"\n=== demand x{cs} (expected consignments/day: {sum(g['lam'][1:]):.0f}) ===")
    print(f"current allocation: {tot_b.mean()/60:.2f} h/day total, overtime {over_b.mean():.0f} min/day")
    for k in (1, 2, 3):
        alloc = list(g["base_alloc"]); cls = [0] * n
        for r in top:
            i = idx[r["name"]]; alloc[i] = RUNS.index(r[f"run_{k}"])
            cls[i] = 0 if r[f"day_class_{k}"] == "daily" else int(r[f"day_class_{k}"])
        train.load(alloc, cls); _, cls = local_search(train, [], "sched", 8, verbose=False)     # best rotation at this demand
        T, O = evaluate(alloc, cls)
        d = tot_b - sum(T); se = d.std(ddof=1) / np.sqrt(len(d))
        per_run = [(Tb[r] - T[r]).mean() for r in range(3)]
        dover = over_b.mean() - sum(O).mean()
        row = dict(demand=cs, allocation=k, saved_min_per_day=d.mean(), ci95=1.96 * se, hamilton=per_run[0], portland=per_run[1],
                   warrnambool=per_run[2], overtime_saved_min_per_day=dover, saved_hours_per_year=d.mean() * WORKDAYS_PER_YEAR / 60,
                   pct_time=100 * d.mean() / tot_b.mean())
        out_rows.append(row)
        print(f"allocation {k}: saves {d.mean():5.1f} min/day (95% CI +-{1.96*se:.1f}) = {row['pct_time']:.1f}% of van time | "
              f"Hamilton {per_run[0]:+.0f}, Portland {per_run[1]:+.0f}, Warrnambool {per_run[2]:+.0f} min/day | "
              f"overtime -{dover:.0f} min/day | ~{row['saved_hours_per_year']:.0f} h/year")
with open(DATA / "allocation_savings.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(out_rows[0])); w.writeheader(); w.writerows(out_rows)
print("\nwrote data/allocation_savings.csv")
