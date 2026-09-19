#!/usr/bin/env python3
"""Map of the proposed run changes: robust moves (chosen in >= 3 of 4 settings) solid, fragile larger moves hollow.
Inputs (local): data/nodes.csv, data/robust_moves.csv, data/optimized_allocation_B_main.csv, data/georef.txt,
data/run_masks.npz, data/region_locality_polygons.json.   Output: proposed_reallocation_map.png
"""
import csv, json, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.lines import Line2D

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
to_px = lambda lon, lat: (ax_ * lon + bx_, ay_ * merc(lat) + by_)
COL = {"Hamilton": "#7b1fa2", "Portland": "#1b5e20", "Warrnambool": "#0d47a1"}

nodes = {r["name"]: r for r in csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8"))}
main = {r["name"]: r for r in csv.DictReader(open(DATA / "optimized_allocation_B_main.csv", encoding="utf-8"))}
robust = {r["name"]: r for r in csv.DictReader(open(DATA / "robust_moves.csv", encoding="utf-8"))}
fragile = [r for r in main.values() if r["changed"] == "1" and r["name"] not in robust and int(r["population"]) >= 100]

fig, ax = plt.subplots(figsize=(14, 8.2), dpi=120)
ax.set_facecolor("#dbe7f0")
polys = json.loads((DATA / "region_locality_polygons.json").read_text())
ax.add_collection(PolyCollection([[to_px(lo, la) for lo, la in ring] for p in polys for ring in p["rings"]],
                                 facecolors="#f4f1ea", edgecolors="#ffffff", linewidths=0.3))
masks = np.load(DATA / "run_masks.npz")
for name, c in COL.items():
    ax.contour(masks[name].astype(float), levels=[0.5], colors=[c], linewidths=2.0, alpha=0.9)
for name, r in main.items():                                             # every locality, coloured by its current run
    nd = nodes[name]; ax.plot(int(nd["px"]), int(nd["py"]), "o", ms=3.2, color=COL[r["baseline_run"]], alpha=0.55, zorder=3)
for city in ("Warrnambool", "Portland (Vic.)", "Hamilton (Vic.)"):
    nd = nodes[city]; ax.plot(int(nd["px"]), int(nd["py"]), "*", ms=15, color="black", zorder=6)
    ax.annotate(city.replace(" (Vic.)", ""), (int(nd["px"]), int(nd["py"])), xytext=(6, -12), textcoords="offset points", fontsize=9, weight="bold", zorder=7)

def label(name, dest_col, dy):
    nd = nodes[name]; ax.annotate(f"{name.replace(' (Vic.)', '')} ({int(nd['pop']):,})", (int(nd["px"]), int(nd["py"])),
                                  xytext=(6, dy), textcoords="offset points", fontsize=7.5, zorder=8,
                                  bbox=dict(boxstyle="round,pad=0.12", fc="white", ec=dest_col, lw=0.8, alpha=0.9))
for k, (name, r) in enumerate(sorted(robust.items(), key=lambda kv: -int(kv[1]["population"]))):
    nd = nodes[name]; ax.plot(int(nd["px"]), int(nd["py"]), "o", ms=11, mfc=COL[r["to_run"]], mec=COL[r["from_run"]], mew=2.6, zorder=6)
    if int(r["population"]) >= 60: label(name, COL[r["to_run"]], 7 if k % 2 == 0 else -13)
for k, r in enumerate(sorted(fragile, key=lambda r: -int(r["population"]))):
    nd = nodes[r["name"]]; ax.plot(int(nd["px"]), int(nd["py"]), "D", ms=9, mfc="none", mec=COL[r["new_run"]], mew=2, zorder=6)
    label(r["name"], COL[r["new_run"]], 8 if k % 2 == 0 else -14)

ax.legend(handles=[Line2D([0], [0], marker="o", ls="", ms=10, mfc="#1b5e20", mec="#7b1fa2", mew=2.4, label="robust move (fill = new run, edge = old run)"),
                   Line2D([0], [0], marker="D", ls="", ms=8, mfc="none", mec="#1b5e20", mew=2, label="larger move that depends on assumptions (edge = new run)"),
                   Line2D([0], [0], marker="o", ls="", ms=4, color="#777", label="other localities (colour = current run)"),
                   *[Line2D([0], [0], color=c, lw=2, label=n + " outline") for n, c in COL.items()]],
          loc="lower left", fontsize=8, framealpha=0.92)
ax.set_xlim(20, 1060); ax.set_ylim(950, 380); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
ax.set_title("Proposed run changes from the first optimization attempt (3-day rotation model, calibrated on one sample day)", fontsize=10)
fig.tight_layout(); fig.savefig(BASE / "proposed_reallocation_map.png", dpi=120)
print("saved proposed_reallocation_map.png |", len(robust), "robust,", len(fragile), "fragile (pop >= 100) markers")
