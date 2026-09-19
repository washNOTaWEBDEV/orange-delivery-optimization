#!/usr/bin/env python3
"""Population density map (2021 Census, persons per km2 by locality) over the run map screenshot frame.

Inputs (all local, git-ignored): data/vic_locality_population_2021.csv, data/georef.txt,
data/run_masks.npz (run outlines read from the screenshot). Locality boundaries are fetched
from public ABS data if data/region_locality_polygons.json is missing.
Output: population_density_map.png
"""
import csv, json, math, time, urllib.parse, urllib.request
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.colors import LogNorm

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
W, H = 1381, 970                                     # screenshot size in pixels
ax_, bx_, ay_, by_ = map(float, (DATA / "georef.txt").read_text().split())
merc = lambda lat: math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
to_px = lambda lon, lat: (ax_ * lon + bx_, ay_ * merc(lat) + by_)

def to_lonlat(x, y):
    m = (y - by_) / ay_
    return (x - bx_) / ax_, math.degrees(2 * math.atan(math.exp(m)) - math.pi / 2)

def fetch_polygons(path):
    (lon0, lat1), (lon1, lat0) = to_lonlat(0, 0), to_lonlat(W, H)
    env = f"{lon0 - .1},{lat0 - .1},{lon1 + .1},{lat1 + .1}"
    url = "https://geo.abs.gov.au/arcgis/rest/services/ASGS2021/SAL/MapServer/0/query"
    out, offset = [], 0
    while True:
        q = {"where": "state_code_2021='2'", "geometry": env, "geometryType": "esriGeometryEnvelope",
             "inSR": "4326", "spatialRel": "esriSpatialRelIntersects",
             "outFields": "sal_code_2021,sal_name_2021", "returnGeometry": "true", "outSR": "4326",
             "maxAllowableOffset": "0.002", "geometryPrecision": "5", "orderByFields": "objectid",
             "resultOffset": str(offset), "resultRecordCount": "400", "f": "json"}
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(q),
                                     headers={"User-Agent": "delivery-run-analysis/0.1 (research)"})
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.load(r)
        feats = d.get("features", [])
        for f in feats:
            if f.get("geometry", {}).get("rings"):
                out.append({"code": "SAL" + f["attributes"]["sal_code_2021"], "name": f["attributes"]["sal_name_2021"],
                            "rings": f["geometry"]["rings"]})
        if len(feats) < 400 and not d.get("exceededTransferLimit"):
            break
        offset += len(feats); time.sleep(1)
    path.write_text(json.dumps(out))
    return out

polys_path = DATA / "region_locality_polygons.json"
polys = json.loads(polys_path.read_text()) if polys_path.exists() else fetch_polygons(polys_path)

pop = {}
with open(DATA / "vic_locality_population_2021.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        pop[r["sal_code"]] = (int(r["total_persons_2021"]), float(r["area_sqkm"]), r["name_plain"])

def density(code):
    p = pop.get(code)
    return None if p is None or p[1] <= 0 else p[0] / p[1]

# draw big polygons first so enclaves and small suburbs stay visible on top
def bbox_area(rings):
    xs = [p[0] for r in rings for p in r]; ys = [p[1] for r in rings for p in r]
    return (max(xs) - min(xs)) * (max(ys) - min(ys))
polys.sort(key=lambda p: -bbox_area(p["rings"]))
shapes, values, zero_shapes = [], [], []
for p in polys:
    d = density(p["code"])
    for ring in p["rings"]:
        pts = [to_px(lon, lat) for lon, lat in ring]
        if d is None or d <= 0:
            zero_shapes.append(pts)
        else:
            shapes.append(pts); values.append(d)

fig, ax = plt.subplots(figsize=(14, 9.8), dpi=120)
ax.set_facecolor("#dbe7f0")                            # sea
if zero_shapes:
    ax.add_collection(PolyCollection(zero_shapes, facecolors="#ececec", edgecolors="none"))
pc = PolyCollection(shapes, array=np.array(values), cmap="YlOrRd", norm=LogNorm(vmin=0.1, vmax=3000),
                    edgecolors="#ffffff", linewidths=0.15)
ax.add_collection(pc)

masks = np.load(DATA / "run_masks.npz")
for name, colr in {"Hamilton": "#7b1fa2", "Portland": "#1b5e20", "Warrnambool": "#0d47a1"}.items():
    ax.contour(masks[name].astype(float), levels=[0.5], colors=[colr], linewidths=2.2)

# labels: larger places in the frame plus the towns this analysis cares about
coords = {}
with open(DATA / "vic_locality_coords.csv", newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        coords[r["sal_code"]] = (float(r["lon"]), float(r["lat"]), r["name"])
always = {"Hawkesdale", "Horsham", "Macarthur (Vic.)", "Mortlake (Vic.)", "Simpson (Vic.)"}
labelled = []
for code, (lon, lat, name) in coords.items():
    x, y = to_px(lon, lat)
    if not (0 <= x < W and 0 <= y < H) or code not in pop:
        continue
    if (pop[code][0] >= 2500 and x < 1050) or name in always:
        labelled.append((x, y, pop[code][2], pop[code][0]))
for x, y, n, p in labelled:
    ax.plot(x, y, "o", ms=3.2, color="black", zorder=5)
    ax.annotate(f"{n} {p:,}", (x, y), xytext=(4, 3), textcoords="offset points", fontsize=7.5, zorder=6,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.7))
gx, gy = to_px(144.36186, -38.15004)
ax.plot(gx, gy, "s", ms=8, color="#111", zorder=7); ax.annotate("Depot (Geelong)", (gx, gy), xytext=(-72, -14),
                                                                  textcoords="offset points", fontsize=8, weight="bold", zorder=8)

from matplotlib.lines import Line2D
ax.legend(handles=[Line2D([0], [0], color=c, lw=2.2, label=n + " outline") for n, c in
                   {"Hamilton": "#7b1fa2", "Portland": "#1b5e20", "Warrnambool": "#0d47a1"}.items()],
          loc="lower left", fontsize=8, framealpha=0.85)
ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([])
cb = fig.colorbar(pc, ax=ax, fraction=0.025, pad=0.01)
cb.ax.set_title("persons/km²\n(log scale)", fontsize=8)
ax.set_title("Population density by locality, western Victoria\nRun outlines (Hamilton purple, Portland green, Warrnambool blue) are read from the map screenshot; "
             "labels show total persons", fontsize=10)
fig.tight_layout()
out = BASE / "population_density_map.png"
fig.savefig(out, dpi=120)
print("saved", out, "| localities drawn:", len(shapes) + len(zero_shapes), "| labelled:", len(labelled))
