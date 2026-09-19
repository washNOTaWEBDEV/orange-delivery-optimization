#!/usr/bin/env python3
"""Which localities touch, and along how many km of border, from the fetched boundary polygons (for the compactness penalty).

Rasterises every locality polygon onto the screenshot frame (2x resolution, about 0.12 km per pixel), closes the thin gaps left by
boundary simplification, and counts neighbouring pixel pairs that belong to different localities.
Output (local): data/adjacency.json = [[node_i, node_j, border_km], ...] for nodes in data/nodes.csv.
"""
import csv, json, math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
W, H, S = 1381, 970, 2
KM_PER_PX = 111.32 * math.cos(math.radians(38.3)) / ax_ / S      # km covered by one raster pixel at this latitude
MIN_KM = 0.4                                                       # ignore slivers shorter than this

nodes = list(csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")))
node_of = {nd["sal_code"]: i for i, nd in enumerate(nodes) if i >= 1}
polys = json.loads((DATA / "region_locality_polygons.json").read_text())
def bbox_area(rings):
    xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))
polys.sort(key=lambda p: -bbox_area(p["rings"]))
img = Image.new("I", (W * S, H * S), 0); dr = ImageDraw.Draw(img); next_other = 100000
for p in polys:
    if p["code"] in node_of: pid = node_of[p["code"]]
    else: pid = next_other; next_other += 1                       # localities outside the analysis still block adjacency
    for ring in p["rings"]:
        dr.polygon([((ax_ * lo + bx_) * S, (ay_ * merc(la) + by_) * S) for lo, la in ring], fill=pid)
arr = np.array(img, dtype=np.int64)
painted = arr > 0
dist, (iy, ix) = ndi.distance_transform_edt(~painted, return_indices=True)
arr = np.where(dist <= 2.5, arr[iy, ix], 0)                       # close gaps of a couple of pixels, but not the sea

edges = {}
for a, b in ((arr[:, :-1], arr[:, 1:]), (arr[:-1, :], arr[1:, :])):
    m = (a != b) & (a > 0) & (b > 0) & (a < 100000) & (b < 100000)
    if not m.any(): continue
    pairs = np.stack([np.minimum(a[m], b[m]), np.maximum(a[m], b[m])], axis=1)
    u, c = np.unique(pairs, axis=0, return_counts=True)
    for (i, j), cnt in zip(u, c): edges[(int(i), int(j))] = edges.get((int(i), int(j)), 0) + int(cnt)
out = [[i, j, round(c * KM_PER_PX, 2)] for (i, j), c in sorted(edges.items()) if c * KM_PER_PX >= MIN_KM]
json.dump(out, open(DATA / "adjacency.json", "w"))
deg = np.zeros(len(nodes), int)
for i, j, _ in out: deg[i] += 1; deg[j] += 1
print(f"{len(out)} adjacent pairs among {len(nodes)-1} node localities; mean neighbours {deg[1:].mean():.1f}; "
      f"nodes with no neighbour: {[nodes[i]['name'] for i in range(1, len(nodes)) if deg[i] == 0][:8]}; total border {sum(e[2] for e in out):,.0f} km")
idx = {nd["name"]: i for i, nd in enumerate(nodes)}
nb = {}
for i, j, w in out: nb.setdefault(i, []).append((w, j)); nb.setdefault(j, []).append((w, i))
for name in ("Warrnambool", "Hawkesdale"):
    print(f"  {name} borders:", ", ".join(f"{nodes[j]['name']} {w:.0f} km" for w, j in sorted(nb.get(idx[name], []), reverse=True)[:6]))
