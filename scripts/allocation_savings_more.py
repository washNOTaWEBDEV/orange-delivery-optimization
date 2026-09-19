#!/usr/bin/env python3
"""Paired comparison, on the same untouched simulated days, of the allocations in data/more_runs_allocations<tag>.csv
against the current allocation (day classes taken from the file; the current allocation's rotation is re-optimised)."""
import argparse, csv, io, contextlib, runpy, sys
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
ap = argparse.ArgumentParser(); ap.add_argument("--tag", required=True); ap.add_argument("--mu", default="0.0"); a = ap.parse_args()
sys.argv = ["optimize_more_runs.py", "--mu", a.mu, "--days", "900", "--val-days", "3000", "--passes", "8"]
with contextlib.redirect_stdout(io.StringIO()):
    g = runpy.run_path(str(BASE / "scripts" / "optimize_more_runs.py"), run_name="not_main")     # definitions only, no search
Sim, nodes, n, BASE_RUNS, base_alloc, init_classes, local_search = g["Sim"], g["nodes"], g["n"], g["BASE_RUNS"], g["base_alloc"], g["init_classes"], g["local_search"]
idx = {nd["name"]: i for i, nd in enumerate(nodes)}; CAP = g["CAP"]
rows = list(csv.DictReader(open(DATA / f"more_runs_allocations{a.tag}.csv", encoding="utf-8")))
keys = sorted({c[4:] for c in rows[0] if c.startswith("run_")})
test = Sim(3000, seed=123)
def evaluate(alloc, cls, R):
    test.load(alloc, cls, R); T = [np.array(test.T[r]) for r in range(R)]
    return T, sum(np.maximum(t - CAP, 0) for t in T)
train = Sim(900, seed=3000); cls0 = init_classes(base_alloc, 3); train.load(base_alloc, cls0, 3)
_, cur_cls, _ = local_search(train, 8, 0, move_runs=False)
Tb, ob = evaluate(base_alloc, cur_cls, 3); tb = sum(Tb)
print(f"current: {tb.mean()/60:.2f} h/day, over 12 h {ob.mean():.0f} min/day")
for key in keys:
    R = int(key.split("_")[0]); alloc = list(base_alloc); cls = [0] * n
    for r in rows:
        i = idx[r["name"]]; alloc[i] = (BASE_RUNS + [f"Extra run {x}" for x in range(1, 6)]).index(r[f"run_{key}"])
        cls[i] = 0 if r[f"day_class_{key}"] == "daily" else int(r[f"day_class_{key}"])
    T, o = evaluate(alloc, cls, R); tot = sum(T); d = tb - tot; se = d.std(ddof=1) / np.sqrt(len(d))
    changed = [i for i in range(1, n) if alloc[i] != base_alloc[i]]
    print(f"allocation {key}: saves {d.mean():5.1f} min/day (95% CI +-{1.96*se:.1f}) = {100*d.mean()/tb.mean():.1f}% | "
          + ", ".join(f"{BASE_RUNS[r]} {(Tb[r]-T[r]).mean():+.0f}" for r in range(3)) + " min/day | "
          f"over-12h time {ob.mean()-o.mean():+.0f} min/day saved | ~{d.mean()*250/60:.0f} h/year | {len(changed)} localities changed "
          f"({sum(int(nodes[i]['pop']) for i in changed):,} people)")
