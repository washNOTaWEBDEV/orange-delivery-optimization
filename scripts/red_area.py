#!/usr/bin/env python3
"""Turn the red loop the problem owner drew on a map screenshot into a list of localities.

Input (local): data/red_area_image.png (the annotated map crop), data/vic_locality_coords.csv, data/vic_locality_population_2021.csv,
data/nodes.csv (localities already analysed).
Steps: georeference the crop from labelled towns, fill the loop, list the localities whose centre is inside it.
Outputs (local): data/red_area_georef.txt, data/red_area_mask.npy, data/red_area_localities.csv, data/red_area_outline_points.json
The loop was drawn roughly; localities outside it (for example Colac) are not included.
"""
import csv, json, math, re
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi

DATA = Path(__file__).resolve().parents[1] / "data"
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
img = np.asarray(Image.open(DATA / "red_area_image.png").convert("RGB")).astype(int); H, W, _ = img.shape
red = (img[:, :, 0] > 200) & (img[:, :, 1] < 90) & (img[:, :, 2] < 90)

# 1) georeference: label centres read off the crop (pixel x, y) against locality centres
coords = {}
for r in csv.DictReader(open(DATA / "vic_locality_coords.csv", encoding="utf-8")):
    coords.setdefault(re.sub(r"\s*\((Vic\.?|VIC)\)$", "", r["name"]).lower(), []).append((float(r["lon"]), float(r["lat"])))
CONTROL = [("Woorndoo", 265, 12), ("Caramut", 95, 66), ("Hexham", 198, 95), ("Lismore", 596, 63), ("Mortlake", 272, 158), ("Woolsthorpe", 65, 239),
           ("Grassmere", 95, 296), ("Noorat", 343, 243), ("Terang", 333, 282), ("Camperdown", 476, 277), ("Cobden", 433, 349), ("Beeac", 773, 245),
           ("Colac", 747, 359), ("Warrnambool", 82, 383), ("Nullawarre", 236, 456), ("Timboon", 372, 468), ("Simpson", 512, 479), ("Port Campbell", 383, 571)]
pts = [(n, x, y, *coords[n.lower()][0]) for n, x, y in CONTROL if len(coords.get(n.lower(), [])) == 1]
for _ in range(3):
    ax, bx = np.polyfit([q[3] for q in pts], [q[1] for q in pts], 1); ay, by = np.polyfit([merc(q[4]) for q in pts], [q[2] for q in pts], 1)
    bad = [q[0] for q in pts if math.hypot(q[1] - (ax * q[3] + bx), q[2] - (ay * merc(q[4]) + by)) > 18]
    if not bad: break
    pts = [q for q in pts if q[0] not in bad]                     # drop mis-read labels and refit
(DATA / "red_area_georef.txt").write_text(f"{ax} {bx} {ay} {by}\n")
rms = math.sqrt(sum((q[1] - (ax * q[3] + bx)) ** 2 + (q[2] - (ay * merc(q[4]) + by)) ** 2 for q in pts) / len(pts))
print(f"georeference: {len(pts)} control points, rms {rms:.1f} px")

# 2) fill the loop
seed = (450, 180)                                                 # a point well inside it
for r in range(1, 12):
    barrier = ndi.binary_dilation(red, structure=np.ones((3, 3), bool), iterations=r)
    lab, _ = ndi.label(~barrier); comp = lab == lab[seed[1], seed[0]]
    if not (comp[0].any() or comp[-1].any() or comp[:, 0].any() or comp[:, -1].any()) and comp.sum() > 20000:
        interior = ndi.binary_fill_holes(ndi.binary_dilation(comp, structure=np.ones((3, 3), bool), iterations=r) & (barrier | comp)); break
else:
    raise SystemExit("the loop did not close")
np.save(DATA / "red_area_mask.npy", interior)

# 3) localities whose centre is inside
dist_in = ndi.distance_transform_edt(interior)
pop = {r["sal_code"]: r for r in csv.DictReader(open(DATA / "vic_locality_population_2021.csv", encoding="utf-8"))}
old = {r["sal_code"] for r in csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")) if r.get("new_area") != "1"}   # towns analysed before the area was added
rows = []
for r in csv.DictReader(open(DATA / "vic_locality_coords.csv", encoding="utf-8")):
    if r["sal_code"] not in pop: continue
    lon, lat = float(r["lon"]), float(r["lat"]); px, py = ax * lon + bx, ay * merc(lat) + by
    if 0 <= px < W and 0 <= py < H and interior[int(round(py)), int(round(px))]:
        km = min(dist_in[int(round(py)), int(round(px))], 99) * 111.32 * math.cos(math.radians(38.3)) / ax
        rows.append((r["sal_code"], r["name"], int(pop[r["sal_code"]]["total_persons_2021"]), r["sal_code"] in old, round(km, 1)))
rows.sort(key=lambda x: -x[2])
with open(DATA / "red_area_localities.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["sal_code", "name", "population", "already_a_node", "km_inside_line"]); w.writerows(rows)
edge = ndi.binary_dilation(interior) ^ interior; ys, xs = np.nonzero(edge)
json.dump([[(x - bx) / ax, math.degrees(2 * math.atan(math.exp((y - by) / ay)) - math.pi / 2)] for x, y in zip(xs[::3], ys[::3])],
          open(DATA / "red_area_outline_points.json", "w"))
new = [x for x in rows if not x[3]]
print(f"{len(rows)} localities inside the loop ({sum(x[2] for x in rows):,} people); new to the analysis: {len(new)} ({sum(x[2] for x in new):,} people)")
