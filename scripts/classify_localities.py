#!/usr/bin/env python3
"""Place every Victorian locality on the map screenshot and test it against the run outlines.

Inputs (local, git-ignored): data/vic_locality_coords.csv, data/vic_locality_population_2021.csv,
data/georef.txt, data/run_masks.npz. Outputs: data/localities_by_run_from_image.csv (inside >= 1 outline)
and data/borderline_localities_from_image.csv (within ~3 km of an outline).
"""
import csv, math, re, collections
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
RUNS = ("Hamilton", "Portland", "Warrnambool")
LIMIT_PX, KM_PER_PX = 12, 0.24                       # about 3 km at this scale

raw = dict(np.load(DATA / "run_masks.npz"))
masks = {k: ndi.binary_fill_holes(v) for k, v in raw.items()}     # false-positive blobs left holes
for k in RUNS:
    print(f"{k}: filled {int(masks[k].sum() - raw[k].sum())} hole pixels")
np.savez_compressed(DATA / "run_masks.npz", **masks)
H, W = masks["Hamilton"].shape
sd = {n: ndi.distance_transform_edt(m) - ndi.distance_transform_edt(~m) for n, m in masks.items()}   # + inside

pop = {}
with open(DATA / "vic_locality_population_2021.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        pop[r["sal_code"]] = r
inside_rows, border_rows = [], []
with open(DATA / "vic_locality_coords.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["sal_code"] not in pop:
            continue
        lon, lat = float(r["lon"]), float(r["lat"])
        px, py = ax_ * lon + bx_, ay_ * merc(lat) + by_
        if not (0 <= px < W and 0 <= py < H):
            continue
        ix, iy = int(round(px)), int(round(py))
        d = {n: float(sd[n][iy, ix]) for n in RUNS}
        runs = [n for n in RUNS if d[n] > 0]
        p = pop[r["sal_code"]]
        base = {"sal_code": r["sal_code"], "name": r["name"], "lon": lon, "lat": lat, "px": round(px), "py": round(py),
                "total_persons_2021": int(p["total_persons_2021"]), "area_sqkm": p["area_sqkm"]}
        if runs:
            inside_rows.append({**base, "runs": "|".join(runs)})
        near = {n: round(d[n] * KM_PER_PX, 1) for n in RUNS if abs(d[n]) <= LIMIT_PX}
        if near:
            border_rows.append((int(p["total_persons_2021"]), r["name"], "+".join(runs), near))

order = {n: i for i, n in enumerate(RUNS)}
inside_rows.sort(key=lambda r: (min(order[x] for x in r["runs"].split("|")), r["runs"], -r["total_persons_2021"]))
with open(DATA / "localities_by_run_from_image.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(inside_rows[0])); w.writeheader(); w.writerows(inside_rows)
border_rows.sort(reverse=True)
with open(DATA / "borderline_localities_from_image.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["name", "total_persons_2021", "inside_runs", "signed_km_to_nearby_outlines"])
    for pp, name, runs, dist in border_rows:
        w.writerow([name, pp, runs, dist])

cat = collections.defaultdict(lambda: [0, 0])
for r in inside_rows:
    cat[r["runs"]][0] += 1; cat[r["runs"]][1] += r["total_persons_2021"]
print(f"\n{len(inside_rows)} localities inside >= 1 outline; {len(border_rows)} within ~3 km of an outline")
for k, (n, p) in sorted(cat.items(), key=lambda kv: (len(kv[0]), kv[0])):
    print(f"  {k:<28}{n:>5} localities {p:>8,} people")
