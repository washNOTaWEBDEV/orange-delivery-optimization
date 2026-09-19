#!/usr/bin/env python3
"""One image per top allocation: localities shaded by the run they are allocated to, moved localities outlined and labelled.
Inputs (local): data/top3_allocations.csv, data/top3_summary.json, data/nodes.csv, data/region_locality_polygons.json,
data/georef.txt, data/run_masks.npz.   Outputs: allocation_1.png, allocation_2.png, allocation_3.png
"""
import csv, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
to_px = lambda lon, lat: (ax_ * lon + bx_, ay_ * merc(lat) + by_)
RUNS = ["Hamilton", "Portland", "Warrnambool"]
COL = {"Hamilton": "#8e44ad", "Portland": "#27ae60", "Warrnambool": "#2980b9"}
EDGE = {"Hamilton": "#7b1fa2", "Portland": "#1b5e20", "Warrnambool": "#0d47a1"}

nodes = list(csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")))
code_of = {}
for nd in nodes:
    assert nd["name"] not in code_of, "duplicate locality name " + nd["name"]
    code_of[nd["name"]] = nd["sal_code"]
alloc_rows = list(csv.DictReader(open(DATA / "top3_allocations.csv", encoding="utf-8")))
summary = json.load(open(DATA / "top3_summary.json"))
polys = json.loads((DATA / "region_locality_polygons.json").read_text())
poly_px = {p["code"]: [[to_px(lo, la) for lo, la in ring] for ring in p["rings"]] for p in polys}
masks = np.load(DATA / "run_masks.npz")
POP_CITIES = {"Warrnambool": "Warrnambool", "Portland (Vic.)": "Portland", "Hamilton (Vic.)": "Hamilton"}

for k in (1, 2, 3):
    info = summary[k]; st = info["stats"]
    run_of = {r["name"]: r[f"run_{k}"] for r in alloc_rows}
    cur_of = {r["name"]: r["current_run"] for r in alloc_rows}
    changed = [r for r in alloc_rows if r[f"run_{k}"] != r["current_run"]]
    fig, ax = plt.subplots(figsize=(13, 11.2), dpi=110)
    ax.set_facecolor("#dbe7f0")
    grey, cols, edges, lws = [], [], [], []
    for code, rings in poly_px.items():
        pass
    name_of_code = {v: kk for kk, v in code_of.items()}
    for code, rings in poly_px.items():
        nm = name_of_code.get(code)
        for ring in rings:
            if nm is None:
                grey.append(ring)
            else:
                run = run_of[nm]; moved = run != cur_of[nm]
                cols.append(COL[run]); edges.append("black" if moved else "white"); lws.append(1.8 if moved else 0.25)
                grey.append(None)
    ax.add_collection(PolyCollection([g for g in grey if g is not None], facecolors="#efece4", edgecolors="white", linewidths=0.25))
    shaped = [ring for code, rings in poly_px.items() if name_of_code.get(code) for ring in rings]
    ax.add_collection(PolyCollection(shaped, facecolors=cols, edgecolors=edges, linewidths=lws, alpha=0.78))
    for run, c in EDGE.items():                                    # the current outlines from the screenshot, for reference
        ax.contour(masks[run].astype(float), levels=[0.5], colors=[c], linewidths=1.2, linestyles="--", alpha=0.8)
    for nd in nodes[1:]:
        if nd["name"] in POP_CITIES:
            ax.plot(float(nd["px"]), float(nd["py"]), "*", ms=16, color="black", zorder=6)
            ax.annotate(POP_CITIES[nd["name"]], (float(nd["px"]), float(nd["py"])), xytext=(7, -13), textcoords="offset points", fontsize=10, weight="bold", zorder=7)
    for j, r in enumerate(sorted(changed, key=lambda r: -int(r["population"]))):
        if int(r["population"]) >= 60 or len(changed) <= 14:
            ax.annotate(f"{r['name'].replace(' (Vic.)', '')} ({int(r['population']):,}) {r['current_run'][:3]}→{r[f'run_{k}'][:3]}",
                        (float(r["px"]), float(r["py"])), xytext=(8, 9 if j % 2 == 0 else -15), textcoords="offset points", fontsize=7.5, zorder=8,
                        bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="black", lw=0.6, alpha=0.9))
    moved_people = sum(int(r["population"]) for r in changed)
    lines = [f"{info['label']}  ({info['name']})", "",
             "Expected van time per day (model):"]
    tot = sum(s["mean"] for s in st)
    lines.append(f"  all three runs: {tot/60:.1f} h")
    for run, s in zip(RUNS, st):
        lines.append(f"  {run:<12} {s['mean']/60:.1f} h, over 12 h on {s['p_over']*100:.0f}% of days")
    lines += ["", f"Changes vs current: {len(changed)} localities, {moved_people:,} people"]
    cur = summary[0]["stats"]; ctot = sum(s["mean"] for s in cur)
    lines.append(f"Current allocation: {ctot/60:.1f} h; Hamilton over 12 h on {cur[0]['p_over']*100:.0f}% of days")
    ax.text(0.015, 0.015, "\n".join(lines), transform=ax.transAxes, fontsize=9, family="monospace", va="bottom",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#555", alpha=0.94), zorder=10)
    ax.legend(handles=[Patch(fc=COL[r], ec="none", label=f"{r} run", alpha=0.78) for r in RUNS] +
                      [Patch(fc="none", ec="black", lw=1.8, label="moved from its current run"),
                       Patch(fc="#efece4", ec="white", label="not in this analysis")],
              loc="upper left", fontsize=9, framealpha=0.95)
    ax.set_xlim(20, 1060); ax.set_ylim(950, 0); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"{info['label']} of the best three: town allocation by run\n(dashed lines = current run outlines from the screenshot)", fontsize=11)
    fig.tight_layout(); out = BASE / f"allocation_{k}.png"; fig.savefig(out, dpi=110); plt.close(fig)
    print("saved", out.name, "|", len(changed), "localities changed,", f"{moved_people:,}", "people")
