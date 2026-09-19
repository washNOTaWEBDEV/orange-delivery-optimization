#!/usr/bin/env python3
"""Images for the allocations found when the number of runs is free: one image per allocation with at least one extra run.
Inputs (local): data/more_runs_allocations.csv, data/more_runs_summary.json, data/nodes.csv, data/region_locality_polygons.json,
data/georef.txt, data/run_masks.npz.   Outputs: allocation_<k>runs_<rank>.png
"""
import argparse, csv, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Patch

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
ap = argparse.ArgumentParser()
ap.add_argument("--tag", default="", help="suffix of the data files, e.g. _mu0.4")
ap.add_argument("--prefix", default="allocation", help="image file name prefix")
ap.add_argument("--label", default="", help="text added to each title")
ap.add_argument("--only", default="", help="comma-separated allocation keys to draw, e.g. 3_1,4_1 (default: all)")
args = ap.parse_args()
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
to_px = lambda lon, lat: (ax_ * lon + bx_, ay_ * merc(lat) + by_)
COL = {"Hamilton": "#8e44ad", "Portland": "#27ae60", "Warrnambool": "#2980b9", "Extra run 1": "#e67e22", "Extra run 2": "#c0392b",
       "Extra run 3": "#16a085"}
EDGE = {"Hamilton": "#7b1fa2", "Portland": "#1b5e20", "Warrnambool": "#0d47a1"}
CITIES = {"Warrnambool": "Warrnambool", "Portland (Vic.)": "Portland", "Hamilton (Vic.)": "Hamilton"}

nodes = list(csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")))
name_of_code = {nd["sal_code"]: nd["name"] for nd in nodes}
rows = list(csv.DictReader(open(DATA / f"more_runs_allocations{args.tag}.csv", encoding="utf-8")))
summ = json.load(open(DATA / f"more_runs_summary{args.tag}.json"))
polys = json.loads((DATA / "region_locality_polygons.json").read_text())
poly_px = {p["code"]: [[to_px(lo, la) for lo, la in ring] for ring in p["rings"]] for p in polys}
masks = np.load(DATA / "run_masks.npz")
cols = sorted({c[4:] for c in rows[0] if c.startswith("run_")})         # e.g. "3_1", "4_1", "4_2", "4_3"
cur = summ["results"]["current"]; cur_total = cur["total_min"]

only = set(filter(None, args.only.split(",")))
for key in cols:
    if only and key not in only: continue
    k = int(key.split("_")[0]); rank = int(key.split("_")[1])
    run_of = {r["name"]: r[f"run_{key}"] for r in rows}; cur_of = {r["name"]: r["current_run"] for r in rows}
    members = {}
    for nm, rn in run_of.items(): members.setdefault(rn, []).append(nm)
    extras = sorted(rn for rn in members if rn.startswith("Extra") and members[rn])
    if len(extras) != k - 3: continue                                    # skip allocations with an empty extra run (they equal a smaller k)
    st = summ["results"][key]; seed = summ["seeds"][key]
    fig, ax = plt.subplots(figsize=(13, 11.2), dpi=110); ax.set_facecolor("#dbe7f0")
    grey, shaped, fc, ec, lw = [], [], [], [], []
    for code, rings in poly_px.items():
        nm = name_of_code.get(code)
        for ring in rings:
            if nm is None: grey.append(ring)
            else:
                rn = run_of[nm]; moved = rn != cur_of[nm]
                shaped.append(ring); fc.append(COL.get(rn, "#7f8c8d")); ec.append("black" if moved else "white"); lw.append(1.6 if moved else 0.25)
    ax.add_collection(PolyCollection(grey, facecolors="#efece4", edgecolors="white", linewidths=0.25))
    ax.add_collection(PolyCollection(shaped, facecolors=fc, edgecolors=ec, linewidths=lw, alpha=0.8))
    for run, c in EDGE.items():
        ax.contour(masks[run].astype(float), levels=[0.5], colors=[c], linewidths=1.2, linestyles="--", alpha=0.8)
    pos = {nd["name"]: (float(nd["px"]), float(nd["py"]), int(nd["pop"])) for nd in nodes[1:]}
    for nm, lab in CITIES.items():
        x, y, _ = pos[nm]; ax.plot(x, y, "*", ms=16, color="black", zorder=6)
        ax.annotate(lab, (x, y), xytext=(7, -13), textcoords="offset points", fontsize=10, weight="bold", zorder=7)
    for rn in extras:                                                     # label the larger towns of each extra run
        big = sorted(members[rn], key=lambda nm: -pos[nm][2])[:7]
        for j, nm in enumerate(big):
            x, y, p = pos[nm]; ax.plot(x, y, "o", ms=5, color="black", zorder=6)
            ax.annotate(f"{nm.replace(' (Vic.)', '')} ({p:,})", (x, y), xytext=(7, 8 if j % 2 == 0 else -14), textcoords="offset points",
                        fontsize=7.5, zorder=8, bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=COL[rn], lw=1, alpha=0.92))
    changed = sum(1 for nm in run_of if run_of[nm] != cur_of[nm])
    tot = st["total_min"]
    lines = [f"{k} runs, option {rank}" + (f" (new run seeded at {seed})" if seed else ""), "", "Expected van time per day (model):",
             f"  all runs: {tot/60:.1f} h  (current allocation {cur_total/60:.1f} h, {(tot-cur_total)/60:+.1f} h)"]
    names = ["Hamilton", "Portland", "Warrnambool"] + [f"Extra run {i}" for i in range(1, k - 2)]
    for rn, s_ in zip(names, st["runs"]):
        if s_["members"] or rn in ("Hamilton", "Portland", "Warrnambool"):
            extra = "" if rn in ("Hamilton", "Portland", "Warrnambool") else f", works {s_['active']*100:.0f}% of days"
            lines.append(f"  {rn:<12} {s_['mean']/60:4.1f} h, over 12 h {s_['p_over']*100:2.0f}% of days, {s_['members']} towns{extra}")
    if "cut_km" in st:
        lines += ["", f"Border between runs: {st['cut_km']:,.0f} km (current {cur['cut_km']:,.0f} km)",
                  "Separate patches per run: " + "/".join(str(c[0]) for c in st["components"]) + " (current " + "/".join(str(c[0]) for c in cur["components"]) + ")"]
    lines += ["", f"Time over 12 h: {st['overtime_min']:.0f} min/day (current {cur['overtime_min']:.0f})",
              f"Days when some run is over 12 h: {st['p_any_over']*100:.0f}% (current {cur['p_any_over']*100:.0f}%)",
              f"Localities in a different run from today: {changed}"]
    ax.text(0.985, 0.985, "\n".join(lines), transform=ax.transAxes, fontsize=8.2, family="monospace", va="top", ha="right",
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="#555", alpha=0.94), zorder=10)
    ax.legend(handles=[Patch(fc=COL[r], ec="none", alpha=0.8, label=f"{r}" + (" run" if not r.startswith("Extra") else " (new)")) for r in
                       ["Hamilton", "Portland", "Warrnambool"] + extras] +
                      [Patch(fc="none", ec="black", lw=1.6, label="in a different run from today"), Patch(fc="#efece4", ec="white", label="not in this analysis")],
              loc="upper left", fontsize=9, framealpha=0.95)
    ax.set_xlim(20, 1060); ax.set_ylim(950, 0); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
    ax.set_title(f"Allocation with {k} runs (option {rank}): town allocation by run{args.label}\n(dashed lines = current run outlines from the screenshot)", fontsize=11)
    fig.tight_layout(); out = BASE / f"{args.prefix}_{k}runs_{rank}.png"; fig.savefig(out, dpi=110); plt.close(fig)
    print("saved", out.name, "| extra runs:", {rn: len(members[rn]) for rn in extras}, "| localities changed:", changed)
