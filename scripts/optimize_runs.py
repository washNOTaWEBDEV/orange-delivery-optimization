#!/usr/bin/env python3
"""First-attempt allocation of towns to the Hamilton, Portland and Warrnambool runs.

Model (all assumptions are printed in the report):
  * every run is one driver, one round trip from the Geelong depot per day; road times from OSRM (data/travel_minutes.npy)
  * demand: a locality generates consignments at c x population per day (population is the problem owner's volume heuristic);
    c is calibrated so the Warrnambool run averages the 36 consignments of the sample day
  * wait rule: a consignment may wait 2 working days (--wait-days), so the driver runs a 3-day rotation: every town has a
    day class (0, 1 or 2) and is visited on its class day when consignments are waiting (probability q = 1 - exp(-3 lambda)),
    delivering 3 lambda / q consignments; the three cities are served every day. The optimiser chooses each
    town's run AND day class, so a run's day-stops are a compact sector
  * time per consignment (driving inside towns, stops, breaks) is calibrated so the sample day comes to 11 h 43 min
  * a run's day = optimal-ish tour through that day's stops + service time; each run is penalised for time over 12 h
Objective: minimise total expected minutes per day (all runs) + KAPPA x expected minutes over 12 h.
"""
import argparse, csv, itertools, math, random, sys, time
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
RUNS = ["Hamilton", "Portland", "Warrnambool"]
CITY = {"Hamilton": "Hamilton (Vic.)", "Portland": "Portland (Vic.)", "Warrnambool": "Warrnambool"}
SAMPLE = ["Waarre", "Port Campbell", "Nullawarre", "Warrnambool", "Illowa", "Yarpturk", "Framlingham", "Panmure", "Ecklin South"]
SAMPLE_MIN, SAMPLE_PARCELS = 11 * 60 + 43, 36
FLOOR_POP, HORSHAM_POP = 25, 40        # people-equivalents: a floor for tiny places; Horsham "rarely appears"
CAP = 720.0

ap = argparse.ArgumentParser()
ap.add_argument("--scenario", default="both", choices=["A", "B", "both", "none"])
ap.add_argument("--cscale", type=float, default=1.0)
ap.add_argument("--days", type=int, default=400)
ap.add_argument("--val-days", type=int, default=2000)
ap.add_argument("--kappa", type=float, default=2.0)
ap.add_argument("--passes", type=int, default=6)
ap.add_argument("--tag", default="")
ap.add_argument("--multistart", type=int, default=0, help="extra whole-reallocation searches on different simulated days; then pick the top 3")
ap.add_argument("--apply-moves", default="", help="CSV with name,to_run: evaluate baseline + these moves")
ap.add_argument("--wait-days", type=int, default=2, help="working days a consignment may wait (2 = the stated rule)")
args = ap.parse_args()
KAPPA = args.kappa
L = args.wait_days + 1                      # rotation length in days: every town is visited on one day in L

nodes = list(csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")))
M = np.load(DATA / "travel_minutes.npy"); Dl = M.tolist(); n = len(nodes)
idx = {nd["name"]: i for i, nd in enumerate(nodes)}
city_idx = {r: idx[CITY[r]] for r in RUNS}
is_city = [False] * n
for r in RUNS: is_city[city_idx[r]] = True
pop_eff = [0.0] * n
for i, nd in enumerate(nodes):
    if i == 0: continue
    pop_eff[i] = HORSHAM_POP if nd["name"] == "Horsham" else max(int(nd["pop"]), FLOOR_POP)

# ---------------- travel-time solver (cheapest insertion + 2-opt + or-opt) ----------------
def _tsp(stops):
    k = len(stops)
    if k == 0: return 0.0
    if k == 1: s = stops[0]; return Dl[0][s] + Dl[s][0]
    if k <= 4:
        return min(Dl[0][p[0]] + sum(Dl[p[i]][p[i + 1]] for i in range(k - 1)) + Dl[p[-1]][0] for p in itertools.permutations(stops))
    far = max(stops, key=lambda s: Dl[0][s]); tour = [0, far, 0]; rem = set(stops); rem.discard(far)
    while rem:
        best = None
        for s in rem:
            for pos in range(len(tour) - 1):
                a, b = tour[pos], tour[pos + 1]; c = Dl[a][s] + Dl[s][b] - Dl[a][b]
                if best is None or c < best[0]: best = (c, s, pos)
        _, s, pos = best; tour.insert(pos + 1, s); rem.discard(s)
    L = len(tour); improved = True
    while improved:
        improved = False
        for i in range(1, L - 2):
            for j in range(i + 1, L - 1):
                a, b, c, d = tour[i - 1], tour[i], tour[j], tour[j + 1]
                if Dl[a][c] + Dl[b][d] - Dl[a][b] - Dl[c][d] < -1e-9:
                    tour[i:j + 1] = tour[i:j + 1][::-1]; improved = True
        for i in range(1, L - 1):
            s, p, q = tour[i], tour[i - 1], tour[i + 1]
            gain = Dl[p][s] + Dl[s][q] - Dl[p][q]; best = None
            for j in range(L - 1):
                if j == i - 1 or j == i: continue
                a, b = tour[j], tour[j + 1]; add = Dl[a][s] + Dl[s][b] - Dl[a][b]
                if add < gain - 1e-9 and (best is None or add < best[0]): best = (add, j)
            if best:
                tour.pop(i); j = best[1]; tour.insert((j if j < i else j - 1) + 1, s); improved = True; break
    return sum(Dl[tour[i]][tour[i + 1]] for i in range(L - 1))

_cache = {}
def tour_time(stops):
    t = _cache.get(stops)
    if t is None:
        t = _cache[stops] = _tsp(tuple(sorted(stops)))
    return t

def held_karp(stops):                      # exact, used once for the calibration tour
    k = len(stops); INF = float("inf")
    dp = {(1 << i, i): Dl[0][stops[i]] for i in range(k)}
    for mask in range(1, 1 << k):
        for last in range(k):
            if (mask, last) not in dp: continue
            for nxt in range(k):
                if mask & (1 << nxt): continue
                key = (mask | (1 << nxt), nxt); v = dp[(mask, last)] + Dl[stops[last]][stops[nxt]]
                if v < dp.get(key, INF): dp[key] = v
    full = (1 << k) - 1
    return min(dp[(full, i)] + Dl[stops[i]][0] for i in range(k))

# ---------------- baseline allocation ----------------
def baseline():
    alloc = [None] * n
    for i, nd in enumerate(nodes):
        if i == 0: continue
        if nd["fixed_run"]: alloc[i] = RUNS.index(nd["fixed_run"]); continue
        ins = nd["inside"].split("|") if nd["inside"] else []
        if len(ins) == 1: alloc[i] = RUNS.index(ins[0])
        elif len(ins) > 1: alloc[i] = min((RUNS.index(r) for r in ins), key=lambda r: Dl[i][city_idx[RUNS[r]]])
        else: alloc[i] = RUNS.index(nd["deepest"])
    return alloc

base_alloc = baseline()
sample_stops = [idx[s] for s in SAMPLE]
sample_drive = held_karp(sample_stops)
sc = (SAMPLE_MIN - sample_drive) / SAMPLE_PARCELS                  # minutes per consignment (stops, in-town driving, breaks)
w_pop = sum(pop_eff[i] for i in range(1, n) if base_alloc[i] == 2)
c = args.cscale * SAMPLE_PARCELS / w_pop
lam = [c * pop_eff[i] for i in range(n)]
q_visit = [0.0 if (i == 0 or is_city[i]) else 1 - math.exp(-L * lam[i]) for i in range(n)]
m_par = [0.0 if q_visit[i] == 0 else L * lam[i] / q_visit[i] for i in range(n)]
print(f"wait rule: {args.wait_days} working days -> {L}-day rotation")
print(f"calibration: sample-day optimal tour drive {sample_drive:.0f} min -> {sc:.1f} min per consignment (incl. breaks);"
      f" c = {c*1000:.3f} consignments per 1000 people per day (cscale {args.cscale})")
print("expected consignments per day:", ", ".join(f"{RUNS[r]} {sum(lam[i] for i in range(1, n) if base_alloc[i] == r):.1f}" for r in range(3)),
      "| cities:", ", ".join(f"{r} {lam[city_idx[r]]:.1f}" for r in RUNS))

# ---------------- simulation state: 3-day rotation ----------------
class Sim:
    def __init__(self, D, seed):
        assert D % L == 0
        self.D = D; rng = np.random.default_rng(seed)
        U = rng.random((D, n)); day_class = np.arange(D) % L
        self.city_parcels = {r: rng.poisson(lam[city_idx[RUNS[r]]], D).astype(float) for r in range(3)}
        self.vis_days = [[np.nonzero((day_class == k) & (U[:, i] < q_visit[i]))[0].tolist() for k in range(L)] for i in range(n)]
    def load(self, alloc, cls):
        self.alloc, self.cls = list(alloc), list(cls); D = self.D
        self.stops = [[None] * D for _ in range(3)]; self.pcs = [[0.0] * D for _ in range(3)]; self.T = [[0.0] * D for _ in range(3)]
        for r in range(3):
            sets = [{city_idx[RUNS[r]]} for _ in range(D)]; pcs = list(self.city_parcels[r])
            for i in range(1, n):
                if self.alloc[i] == r and not is_city[i]:
                    for d in self.vis_days[i][self.cls[i]]: sets[d].add(i); pcs[d] += m_par[i]
            for d in range(D):
                self.stops[r][d] = frozenset(sets[d]); self.pcs[r][d] = pcs[d]
                self.T[r][d] = tour_time(self.stops[r][d]) + sc * pcs[d]
    def stats(self):
        out = []
        for r in range(3):
            t = np.array(self.T[r]); over = np.maximum(t - CAP, 0)
            out.append({"mean": t.mean(), "p_over": float((t > CAP).mean()), "over": over.mean(), "p95": float(np.percentile(t, 95)),
                        "drive": float(np.mean([tour_time(s_) for s_ in self.stops[r]])), "stops": float(np.mean([len(s_) - 1 for s_ in self.stops[r]]))})
        return out
    def J(self):
        return sum(s_["mean"] + KAPPA * s_["over"] for s_ in self.stats())
    def _change(self, r, d, i, sign):
        S = self.stops[r][d]; S2 = (S - {i}) if sign < 0 else (S | {i}); pc = self.pcs[r][d] + sign * m_par[i]
        return S2, pc, tour_time(S2) + sc * pc
    def delta(self, i, a, k0, b, k1):
        if a == b and k0 == k1: return 0.0
        tot = 0.0
        for d in self.vis_days[i][k0]:
            _, _, T2 = self._change(a, d, i, -1); T1 = self.T[a][d]
            tot += (T2 - T1) + KAPPA * (max(T2 - CAP, 0) - max(T1 - CAP, 0))
        for d in self.vis_days[i][k1]:
            _, _, T2 = self._change(b, d, i, +1); T1 = self.T[b][d]
            tot += (T2 - T1) + KAPPA * (max(T2 - CAP, 0) - max(T1 - CAP, 0))
        return tot / self.D
    def commit(self, i, a, k0, b, k1):
        for d in self.vis_days[i][k0]:
            S2, pc, T2 = self._change(a, d, i, -1); self.stops[a][d], self.pcs[a][d], self.T[a][d] = S2, pc, T2
        for d in self.vis_days[i][k1]:
            S2, pc, T2 = self._change(b, d, i, +1); self.stops[b][d], self.pcs[b][d], self.T[b][d] = S2, pc, T2
        self.alloc[i], self.cls[i] = b, k1

def init_classes(alloc):
    """Sector start: farthest-first seeds per run, every town joins its nearest seed (by road time)."""
    cls = [0] * n
    for r in range(3):
        mem = [i for i in range(1, n) if alloc[i] == r and not is_city[i]]
        if len(mem) < L: continue
        seeds = [max(mem, key=lambda i: Dl[city_idx[RUNS[r]]][i])]
        while len(seeds) < L: seeds.append(max(mem, key=lambda i: min(Dl[i][s_] for s_ in seeds)))
        for i in mem: cls[i] = min(range(L), key=lambda k: Dl[i][seeds[k]])
    return cls

def plausible_runs(i):
    near = min(Dl[i][city_idx[r]] for r in RUNS)
    return [b for b, r in enumerate(RUNS) if Dl[i][city_idx[r]] <= near * 1.6 + 25]

def local_search(sim, movable, label, passes, seed=1, verbose=True):
    rnd = random.Random(seed); t0 = time.time(); movable = set(movable)
    nodes_ = [i for i in range(1, n) if not is_city[i] and nodes[i]["fixed_run"] != "" or (not is_city[i])]
    for ps in range(passes):
        order = list(dict.fromkeys(nodes_)); rnd.shuffle(order); moved = 0
        for i in order:
            a, k0 = sim.alloc[i], sim.cls[i]; best = (-0.1, None)       # ignore gains below 0.1 min/day (noise)
            runs_ok = plausible_runs(i) if i in movable else [a]
            for b in runs_ok:
                for k1 in range(L):
                    if b == a and k1 == k0: continue
                    dj = sim.delta(i, a, k0, b, k1)
                    if dj < best[0]: best = (dj, (b, k1))
            if best[1] is not None:
                sim.commit(i, a, k0, best[1][0], best[1][1]); moved += 1
        if verbose: print(f"  [{label}] pass {ps+1}: {moved} moves, J = {sim.J():.1f} ({time.time()-t0:.0f}s, tour cache {len(_cache)})", flush=True)
        if moved == 0: break
    return sim.alloc, sim.cls

def report(title, alloc, cls, val):
    val.load(alloc, cls); st = val.stats()
    tot = sum(s_["mean"] for s_ in st)
    print(f"\n{title}: total {tot/60:.2f} h/day | " + " | ".join(
        f"{RUNS[r]} {st[r]['mean']/60:.2f} h (drive {st[r]['drive']/60:.2f} h, {st[r]['stops']:.1f} stops, P>12h {st[r]['p_over']*100:.0f}%, over {st[r]['over']:.0f} min)" for r in range(3)))
    return st

movable_A = [i for i in range(1, n) if nodes[i]["border"] == "1" and not nodes[i]["fixed_run"]]
movable_B = [i for i in range(1, n) if not nodes[i]["fixed_run"] and not is_city[i]]
print(f"nodes: {n-1} localities; movable in A (borderline): {len(movable_A)}; movable in B (all): {len(movable_B)}")
_h = held_karp(sample_stops); _g = _tsp(tuple(sorted(sample_stops)))
print(f"tour solver check on the sample day: exact {_h:.1f} min, heuristic {_g:.1f} min")

train = Sim(args.days, seed=11); val = Sim(args.val_days, seed=99)
cls0 = init_classes(base_alloc)
print("\n=== Baseline: current outlines, with the best 3-day rotation found for them ===")
train.load(base_alloc, cls0); _, base_cls = local_search(train, [], "baseline schedule", args.passes)
results = {"baseline": (list(base_alloc), list(base_cls))}
base_stats = report("BASELINE (validation days)", base_alloc, base_cls, val)

for scen, mov in (("A", movable_A), ("B", movable_B)):
    if args.scenario not in (scen, "both"): continue
    print(f"\n=== Scenario {scen}: {'only borderline localities may change run' if scen == 'A' else 'every locality may change run'} ===")
    train.load(base_alloc, base_cls); alloc, cls = local_search(train, mov, scen, args.passes)
    results[scen] = (list(alloc), list(cls))
    report(f"Scenario {scen} (validation days)", alloc, cls, val)
    changed = [(nodes[i]["pop"], nodes[i]["name"], RUNS[base_alloc[i]], RUNS[alloc[i]]) for i in range(1, n) if alloc[i] != base_alloc[i]]
    changed.sort(key=lambda x: -int(x[0]))
    print(f"  {len(changed)} localities change run ({sum(int(x[0]) for x in changed):,} people); largest:")
    for pp, name, a_, b_ in changed[:18]: print(f"    {name:<28} {int(pp):>6,}  {a_} -> {b_}")
    with open(DATA / f"optimized_allocation_{scen}{args.tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["name", "population", "baseline_run", "new_run", "changed", "border", "day_class"])
        for i in range(1, n): w.writerow([nodes[i]["name"], nodes[i]["pop"], RUNS[base_alloc[i]], RUNS[alloc[i]], int(alloc[i] != base_alloc[i]), nodes[i]["border"], cls[i] if not is_city[i] else "daily"])

if args.apply_moves:
    to = {r["name"]: RUNS.index(r["to_run"]) for r in csv.DictReader(open(args.apply_moves, encoding="utf-8"))}
    alloc = list(base_alloc)
    for i in range(1, n):
        if nodes[i]["name"] in to: alloc[i] = to[nodes[i]["name"]]
    train.load(alloc, init_classes(alloc)); _, cl = local_search(train, [], "package schedule", args.passes)
    st = report(f"PACKAGE of {len(to)} moves from {args.apply_moves} (validation days)", alloc, cl, val)
    results["package"] = (list(alloc), list(cl))
    print("  overtime minutes/day, baseline -> package:", f"{sum(x['over'] for x in base_stats):.0f} -> {sum(x['over'] for x in st):.0f}")
best_key = "B" if "B" in results else ("A" if "A" in results else None)
if best_key:
    print(f"\nMarginal expected minutes/day of serving each borderline locality from each run, at its best day class (scenario {best_key} allocation; validation days):")
    al, cl = results[best_key]; val.load(al, cl)
    print(f"  {'locality':<26}{'pop':>6}  {'now in':<12}" + "".join(f"{r:>14}" for r in RUNS))
    for i in sorted(movable_A, key=lambda i: -int(nodes[i]["pop"]))[:14]:
        a_, k0 = val.alloc[i], val.cls[i]; row = []
        for b_ in range(3):
            row.append(0.0 if b_ == a_ else min(val.delta(i, a_, k0, b_, k1) for k1 in range(L)))
        print(f"  {nodes[i]['name']:<26}{int(nodes[i]['pop']):>6,}  {RUNS[a_]:<12}" + "".join(f"{v:>+14.1f}" for v in row))


# ---------------- multi-start search and the top three allocations ----------------
if args.multistart:
    import json
    KEEP_DIFF = 5                                    # a chosen allocation must differ from the others in >= 5 localities
    cands = {}
    if "A" in results: cands["A: borderline localities only"] = results["A"]
    if "B" in results: cands["B: whole reallocation, start 0"] = results["B"]
    if "package" in results: cands["Robust package (moves chosen by >= 3 of 4 settings)"] = results["package"]
    for k in range(args.multistart):
        tr = Sim(args.days, seed=1000 + k); tr.load(base_alloc, base_cls)
        al, cl_ = local_search(tr, movable_B, f"start {k}", args.passes, seed=100 + k, verbose=False)
        cands[f"B: whole reallocation, start {k+1}"] = (list(al), list(cl_)); _cache.clear()
        print(f"  multistart {k+1}/{args.multistart} done", flush=True)
    ranked = []
    for name, (al, cl_) in cands.items():
        val.load(al, cl_); ranked.append((val.J(), name)); _cache.clear()
    ranked.sort()
    print("\nAll candidates ranked on the validation days (J = total minutes/day + kappa x overtime minutes/day):")
    for j, name in ranked: print(f"  {j:8.1f}  {name}")
    dist = lambda a, b: sum(1 for i in range(1, n) if a[i] != b[i])
    chosen = []
    for j, name in ranked:
        if all(dist(cands[name][0], cands[o][0]) >= KEEP_DIFF for _, o in chosen): chosen.append((j, name))
        if len(chosen) == 3: break
    test = Sim(args.val_days, seed=123)                # untouched days: never used for training or ranking
    summary = []
    print("\nTOP THREE (numbers below are on the untouched test days):")
    tb = report("Current allocation", base_alloc, base_cls, test); _cache.clear()
    summary.append({"label": "Current allocation", "name": "baseline", "stats": tb, "changed": 0, "people_moved": 0})
    rows = {i: [nodes[i]["name"], nodes[i]["pop"], nodes[i]["px"], nodes[i]["py"], RUNS[base_alloc[i]], nodes[i]["border"]] for i in range(1, n)}
    for rank, (j, name) in enumerate(chosen, 1):
        al, cl_ = cands[name]
        st = report(f"Allocation {rank}: {name}", al, cl_, test); _cache.clear()
        ch = [i for i in range(1, n) if al[i] != base_alloc[i]]
        print(f"    changes vs current: {len(ch)} localities, {sum(int(nodes[i]['pop']) for i in ch):,} people")
        summary.append({"label": f"Allocation {rank}", "name": name, "stats": st, "changed": len(ch), "people_moved": sum(int(nodes[i]['pop']) for i in ch)})
        for i in range(1, n): rows[i] += [RUNS[al[i]], cl_[i] if not is_city[i] else "daily"]
    with open(DATA / "top3_allocations.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f); w.writerow(["name", "population", "px", "py", "current_run", "border"] + sum([[f"run_{k}", f"day_class_{k}"] for k in (1, 2, 3)], []))
        for i in range(1, n): w.writerow(rows[i])
    json.dump(summary, open(DATA / "top3_summary.json", "w"), default=float, indent=1)
    print("wrote data/top3_allocations.csv and data/top3_summary.json")
