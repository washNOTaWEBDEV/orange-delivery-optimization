#!/usr/bin/env python3
"""Build the optimisation node set and fetch road travel times (public OSRM demo server, OpenStreetMap data).

Outputs (local, git-ignored): data/nodes.csv, data/travel_minutes.npy  (node 0 = the Geelong depot).
Nodes: localities inside, or within ~3 km of, a run outline on the map screenshot, minus the areas of the smaller
runs that are ignored for now (the black Cobden/Camperdown/Terang run and the Golden Plains area).
"""
import csv, json, math, re, time, urllib.request
from pathlib import Path
import numpy as np
from scipy import ndimage as ndi

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RUNS = ("Hamilton", "Portland", "Warrnambool")
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
masks = {k: ndi.binary_fill_holes(v) for k, v in np.load(DATA / "run_masks.npz").items()}
H, W = masks["Hamilton"].shape
sd = {n: ndi.distance_transform_edt(m) - ndi.distance_transform_edt(~m) for n, m in masks.items()}
LIMIT_PX = 12
# outline of the black Cobden/Camperdown/Terang run, read off the screenshot (pixel coordinates)
BLACK = [(739,717),(760,695),(785,701),(798,709),(839,708),(857,714),(842,745),(838,766),(817,771),(803,764),(769,750)]
def in_poly(x, y, poly):
    c = False; j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
        j = i
    return c
EXCLUDE_NAMES = {"Cobden", "Camperdown (Vic.)", "Terang", "Noorat"}
SAMPLE = ["Warrnambool", "Waarre", "Port Campbell", "Nullawarre", "Illowa", "Yarpturk", "Framlingham", "Panmure", "Ecklin South"]
FIXED = {"Warrnambool": "Warrnambool", "Portland (Vic.)": "Portland", "Hamilton (Vic.)": "Hamilton",   # the three cities
         "Mortlake (Vic.)": "Hamilton", "Simpson (Vic.)": "Warrnambool", "Horsham": "Hamilton"}        # as stated by the problem owner
RED = set()                                   # localities inside the area the problem owner added (red loop)
if (DATA / "red_area_localities.csv").exists():
    RED = {r["sal_code"] for r in csv.DictReader(open(DATA / "red_area_localities.csv", encoding="utf-8"))}
plain = lambda n: re.sub(r"\s*\((Vic\.?|VIC)\)$", "", n)

pop = {}
with open(DATA / "vic_locality_population_2021.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f): pop[r["sal_code"]] = r
nodes = []
with open(DATA / "vic_locality_coords.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        if r["sal_code"] not in pop: continue
        lon, lat = float(r["lon"]), float(r["lat"])
        px, py = ax_ * lon + bx_, ay_ * merc(lat) + by_
        if not (0 <= px < W and 0 <= py < H): continue
        d = {n: float(sd[n][int(round(py)), int(round(px))]) for n in RUNS}
        inside = [n for n in RUNS if d[n] > 0]
        near = any(abs(v) <= LIMIT_PX for v in d.values())
        is_sample = r["name"] in SAMPLE
        in_red = r["sal_code"] in RED
        old_ok = (inside or near or is_sample) and not (px > 1015 or in_poly(px, py, BLACK) or r["name"] in EXCLUDE_NAMES)   # ignored smaller runs
        if not (old_ok or in_red): continue
        nodes.append({"sal_code": r["sal_code"], "name": r["name"], "plain": plain(r["name"]), "lon": lon, "lat": lat,
                      "pop": int(pop[r["sal_code"]]["total_persons_2021"]), "px": round(px), "py": round(py),
                      "inside": "|".join(inside), "deepest": max(d, key=d.get), "border": int(near or len(inside) > 1),
                      "fixed_run": FIXED.get(r["name"], ""), "new_area": int(in_red and not old_ok)})
nodes.sort(key=lambda n: (-n["pop"], n["name"]))
depot = {"sal_code": "DEPOT", "name": "Depot (Geelong)", "plain": "Depot (Geelong)", "lon": 144.36186, "lat": -38.15004,
         "pop": 0, "px": 0, "py": 0, "inside": "", "deepest": "", "border": 0, "fixed_run": "", "new_area": 0}
nodes = [depot] + nodes
print(f"{len(nodes)-1} localities + depot (of which {sum(n_['new_area'] for n_ in nodes)} in the newly added area); border/overlap: {sum(n['border'] for n in nodes)}; fixed: {sum(bool(n['fixed_run']) for n in nodes)}")
missing = [s for s in SAMPLE if s not in {n['name'] for n in nodes}]
print("sample suburbs missing from nodes:", missing or "none")
with open(DATA / "nodes.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(depot)); w.writeheader(); w.writerows(nodes)

# ---- road travel times: OSRM table service in blocks (the demo server caps a request at 100 coordinates)
n = len(nodes); B = 45
blocks = [list(range(i, min(i + B, n))) for i in range(0, n, B)]
M = np.full((n, n), np.nan)
snap = np.zeros(n)
def table(src, dst):
    idx = list(dict.fromkeys(src + dst))
    pos = {g: k for k, g in enumerate(idx)}
    coords = ";".join(f"{nodes[g]['lon']:.5f},{nodes[g]['lat']:.5f}" for g in idx)
    url = (f"https://router.project-osrm.org/table/v1/driving/{coords}?annotations=duration"
           f"&sources={';'.join(str(pos[g]) for g in src)}&destinations={';'.join(str(pos[g]) for g in dst)}")
    for attempt in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "delivery-run-analysis/0.1 (research)"}), timeout=90) as r:
                d = json.load(r)
            if d.get("code") == "Ok": return d
            print("  OSRM said", d.get("code"), d.get("message"))
        except Exception as e:
            print("  request failed:", e)
        time.sleep(3 * (attempt + 1))
    raise SystemExit("OSRM request failed repeatedly")
t0 = time.time()
for bi, src in enumerate(blocks):
    for bj, dst in enumerate(blocks):
        d = table(src, dst)
        M[np.ix_(src, dst)] = np.array([[np.nan if v is None else v for v in row] for row in d["durations"]]) / 60.0
        if bi == bj:
            for g, s in zip(src, d["sources"]): snap[g] = s["distance"]
        time.sleep(1.0)
    print(f"block row {bi+1}/{len(blocks)} done ({time.time()-t0:.0f}s)")
nan = int(np.isnan(M).sum())
print("unreachable pairs:", nan, "| max snap distance (m):", round(snap.max()), "| nodes snapped > 2 km:", int((snap > 2000).sum()))
M = np.where(np.isnan(M), np.nanmax(M), M)
M = (M + M.T) / 2                                           # road times are near-symmetric
np.save(DATA / "travel_minutes.npy", M)
i = {n_["name"]: k for k, n_ in enumerate(nodes)}
for a, b in (("Depot (Geelong)", "Warrnambool"), ("Depot (Geelong)", "Portland (Vic.)"), ("Depot (Geelong)", "Hamilton (Vic.)"), ("Warrnambool", "Portland (Vic.)"), ("Warrnambool", "Hamilton (Vic.)")):
    print(f"  {a} -> {b}: {M[i[a], i[b]]:.0f} min")
