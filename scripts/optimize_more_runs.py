#!/usr/bin/env python3
"""Allocations when the number of runs is not fixed at three (3 up to --max-runs).

Same model as optimize_runs.py (calibrated on the sample day, 3-day rotation for the 2-day wait, road times from OSRM),
generalised to R runs. Runs 0-2 keep their cities (Hamilton, Portland, Warrnambool); every extra run is a further driver leaving
the Geelong depot each day and has no city. An extra run's day costs nothing when none of its towns is due.
For each number of runs the search seeds the new run around each of the largest towns in turn, re-optimises every town's run
and rotation day, keeps the best on validation days, and reports it on untouched test days.
"""
import argparse, collections, csv, itertools, json, math, multiprocessing, random, time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np

BASE = Path(__file__).resolve().parents[1]; DATA = BASE / "data"
BASE_RUNS = ["Hamilton", "Portland", "Warrnambool"]
CITY = ["Hamilton (Vic.)", "Portland (Vic.)", "Warrnambool"]
SAMPLE_CSV = BASE / "06092026202044_2643887_3b92.csv"          # local, git-ignored: receiver suburbs of the sample day
SAMPLE_MIN = 11 * 60 + 43
FLOOR_POP, HORSHAM_POP, CAP, L = 25, 40, 720.0, 3
run_name = lambda r: BASE_RUNS[r] if r < 3 else f"Extra run {r - 2}"

ap = argparse.ArgumentParser()
ap.add_argument("--max-runs", type=int, default=6)
ap.add_argument("--kappa", type=float, default=10.0, help="cost of a minute over 12 h, relative to a minute of van time")
ap.add_argument("--days", type=int, default=900)
ap.add_argument("--val-days", type=int, default=3000)
ap.add_argument("--anchors", type=int, default=24, help="largest towns tried as the seed of each new run")
ap.add_argument("--seed-size", type=int, default=10, help="towns nearest the anchor that start in the new run")
ap.add_argument("--mu", type=float, default=0.0, help="compactness: cost in minutes of van time per day of each km of border between localities in different runs (0 = off)")
ap.add_argument("--passes", type=int, default=6)
ap.add_argument("--workers", type=int, default=5, help="parallel processes; each needs about 0.5 GB")
ap.add_argument("--starts3", type=int, default=6, help="independent searches for the three-run case")
ap.add_argument("--tag", default="")
args = ap.parse_args()
KAPPA = args.kappa
MU = args.mu

# ---------------- model inputs ----------------
nodes = list(csv.DictReader(open(DATA / "nodes.csv", encoding="utf-8")))
M = np.load(DATA / "travel_minutes.npy"); Dl = M.tolist(); n = len(nodes)
idx = {nd["name"]: i for i, nd in enumerate(nodes)}
city_idx = [idx[c] for c in CITY]
is_city = [False] * n
for c_ in city_idx: is_city[c_] = True
fixed = [None] * n
for i, nd in enumerate(nodes):
    if nd["fixed_run"]: fixed[i] = BASE_RUNS.index(nd["fixed_run"])
pop_eff = [0.0] * n
for i, nd in enumerate(nodes):
    if i: pop_eff[i] = HORSHAM_POP if nd["name"] == "Horsham" else max(int(nd["pop"]), FLOOR_POP)

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
    Lg = len(tour); improved = True
    while improved:
        improved = False
        for i in range(1, Lg - 2):
            for j in range(i + 1, Lg - 1):
                a, b, c, d = tour[i - 1], tour[i], tour[j], tour[j + 1]
                if Dl[a][c] + Dl[b][d] - Dl[a][b] - Dl[c][d] < -1e-9:
                    tour[i:j + 1] = tour[i:j + 1][::-1]; improved = True
        for i in range(1, Lg - 1):
            s, p, q = tour[i], tour[i - 1], tour[i + 1]
            gain = Dl[p][s] + Dl[s][q] - Dl[p][q]; best = None
            for j in range(Lg - 1):
                if j == i - 1 or j == i: continue
                a, b = tour[j], tour[j + 1]; add = Dl[a][s] + Dl[s][b] - Dl[a][b]
                if add < gain - 1e-9 and (best is None or add < best[0]): best = (add, j)
            if best:
                tour.pop(i); j = best[1]; tour.insert((j if j < i else j - 1) + 1, s); improved = True; break
    return sum(Dl[tour[i]][tour[i + 1]] for i in range(Lg - 1))

_cache = {}
def tour_time(stops):
    t = _cache.get(stops)
    if t is None:
        if len(_cache) > 300_000: _cache.clear()      # keeps each worker's memory bounded
        t = _cache[stops] = _tsp(tuple(sorted(stops)))
    return t

def held_karp(stops):
    k = len(stops); INF = float("inf"); dp = {(1 << i, i): Dl[0][stops[i]] for i in range(k)}
    for mask in range(1, 1 << k):
        for last in range(k):
            if (mask, last) not in dp: continue
            for nxt in range(k):
                if mask & (1 << nxt): continue
                key = (mask | (1 << nxt), nxt); v = dp[(mask, last)] + Dl[stops[last]][stops[nxt]]
                if v < dp.get(key, INF): dp[key] = v
    full = (1 << k) - 1
    return min(dp[(full, i)] + Dl[stops[i]][0] for i in range(k))

def baseline():
    alloc = [None] * n
    for i in range(1, n):
        nd = nodes[i]
        if nd["fixed_run"]: alloc[i] = BASE_RUNS.index(nd["fixed_run"]); continue
        ins = nd["inside"].split("|") if nd["inside"] else []
        if len(ins) == 1: alloc[i] = BASE_RUNS.index(ins[0])
        elif len(ins) > 1: alloc[i] = min((BASE_RUNS.index(r) for r in ins), key=lambda r: Dl[i][city_idx[r]])
        else: alloc[i] = BASE_RUNS.index(nd["deepest"])
    return alloc

base_alloc = baseline()
sample_rows = list(csv.DictReader(open(SAMPLE_CSV, encoding="utf-8")))
SAMPLE_PARCELS = len(sample_rows)
sample_stops = [idx[s] for s in sorted({r["Receiver Suburb"].strip() for r in sample_rows})]
sample_drive = held_karp(sample_stops)
sc = (SAMPLE_MIN - sample_drive) / SAMPLE_PARCELS
c_dem = SAMPLE_PARCELS / sum(pop_eff[i] for i in range(1, n) if base_alloc[i] == 2)
lam = [c_dem * pop_eff[i] for i in range(n)]
q_visit = [0.0 if (i == 0 or is_city[i]) else 1 - math.exp(-L * lam[i]) for i in range(n)]
m_par = [0.0 if q_visit[i] == 0 else L * lam[i] / q_visit[i] for i in range(n)]
NB = [[j for j in range(1, n) if j != i and Dl[i][j] <= 60] for i in range(n)]
ADJ = [[] for _ in range(n)]; EDGES = []                          # localities that touch, with shared border in km
if (DATA / "adjacency.json").exists():
    for i_, j_, w_ in json.load(open(DATA / "adjacency.json")):
        ADJ[i_].append((j_, w_)); ADJ[j_].append((i_, w_)); EDGES.append((i_, j_, w_))

def components(alloc, R):
    """Per run: (number of separate patches, share of its towns in the largest patch)."""
    parent = list(range(n))
    def find(x):
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for i, j, w in EDGES:
        if alloc[i] == alloc[j]: parent[find(i)] = find(j)
    out = []
    for r in range(R):
        mem = [i for i in range(1, n) if alloc[i] == r]
        if not mem: out.append((0, 1.0)); continue
        roots = collections.Counter(find(i) for i in mem); out.append((len(roots), max(roots.values()) / len(mem)))
    return out

class Sim:
    def __init__(self, D, seed):
        self.D = D; rng = np.random.default_rng(seed)
        U = rng.random((D, n)); day_class = np.arange(D) % L
        self.city_parcels = [rng.poisson(lam[city_idx[r]], D).astype(float) for r in range(3)]
        self.vis_days = [[np.nonzero((day_class == k) & (U[:, i] < q_visit[i]))[0].tolist() for k in range(L)] for i in range(n)]
    def load(self, alloc, cls, R):
        self.R, self.alloc, self.cls = R, list(alloc), list(cls); D = self.D
        self.stops = [[None] * D for _ in range(R)]; self.pcs = [[0.0] * D for _ in range(R)]; self.T = [[0.0] * D for _ in range(R)]
        for r in range(R):
            sets = [({city_idx[r]} if r < 3 else set()) for _ in range(D)]; pcs = list(self.city_parcels[r]) if r < 3 else [0.0] * D
            for i in range(1, n):
                if self.alloc[i] == r and not is_city[i]:
                    for d in self.vis_days[i][self.cls[i]]: sets[d].add(i); pcs[d] += m_par[i]
            for d in range(D):
                self.stops[r][d] = frozenset(sets[d]); self.pcs[r][d] = pcs[d]
                self.T[r][d] = tour_time(self.stops[r][d]) + sc * pcs[d]
    def stats(self):
        out = []
        for r in range(self.R):
            t = np.array(self.T[r]); over = np.maximum(t - CAP, 0)
            out.append({"mean": float(t.mean()), "p_over": float((t > CAP).mean()), "over": float(over.mean()),
                        "active": float((t > 0).mean()), "members": sum(1 for i in range(1, n) if self.alloc[i] == r and not is_city[i]),
                        "people": sum(int(nodes[i]["pop"]) for i in range(1, n) if self.alloc[i] == r)})
        return out
    def cut_km(self):
        return sum(w for i, j, w in EDGES if self.alloc[i] != self.alloc[j])
    def J(self, kappa=None, mu=None):
        kappa = KAPPA if kappa is None else kappa; mu = MU if mu is None else mu
        return sum(s["mean"] + kappa * s["over"] for s in self.stats()) + mu * self.cut_km()
    def p_any_over(self):
        return float((np.max(np.array(self.T), axis=0) > CAP).mean())
    def _change(self, r, d, i, sign):
        S = self.stops[r][d]; S2 = (S - {i}) if sign < 0 else (S | {i}); pc = self.pcs[r][d] + sign * m_par[i]
        return S2, pc, (tour_time(S2) + sc * pc) if S2 else 0.0
    def delta(self, i, a, k0, b, k1):
        if a == b and k0 == k1: return 0.0
        tot = 0.0
        for d in self.vis_days[i][k0]:
            _, _, T2 = self._change(a, d, i, -1); T1 = self.T[a][d]
            tot += (T2 - T1) + KAPPA * (max(T2 - CAP, 0) - max(T1 - CAP, 0))
        for d in self.vis_days[i][k1]:
            _, _, T2 = self._change(b, d, i, +1); T1 = self.T[b][d]
            tot += (T2 - T1) + KAPPA * (max(T2 - CAP, 0) - max(T1 - CAP, 0))
        comp = 0.0
        if MU and a != b:                                              # compactness: change in border length between runs
            for j, w in ADJ[i]:
                rj = self.alloc[j]; comp += w * ((rj != b) - (rj != a))
        return tot / self.D + MU * comp
    def commit(self, i, a, k0, b, k1):
        for d in self.vis_days[i][k0]:
            S2, pc, T2 = self._change(a, d, i, -1); self.stops[a][d], self.pcs[a][d], self.T[a][d] = S2, pc, T2
        for d in self.vis_days[i][k1]:
            S2, pc, T2 = self._change(b, d, i, +1); self.stops[b][d], self.pcs[b][d], self.T[b][d] = S2, pc, T2
        self.alloc[i], self.cls[i] = b, k1

def init_classes(alloc, R):
    cls = [0] * n
    for r in range(R):
        mem = [i for i in range(1, n) if alloc[i] == r and not is_city[i]]
        if len(mem) < L: continue
        ref = city_idx[r] if r < 3 else 0
        seeds = [max(mem, key=lambda i: Dl[ref][i])]
        while len(seeds) < L: seeds.append(max(mem, key=lambda i: min(Dl[i][s_] for s_ in seeds)))
        for i in mem: cls[i] = min(range(L), key=lambda k: Dl[i][seeds[k]])
    return cls

def near_runs(sim, i):
    rs = {sim.alloc[i]}
    for j in NB[i]: rs.add(sim.alloc[j])
    for r in range(min(3, sim.R)):
        if Dl[i][city_idx[r]] <= 60: rs.add(r)
    return sorted(rs)

def local_search(sim, passes, seed, move_runs=True):
    rnd = random.Random(seed); order = [i for i in range(1, n) if not is_city[i]]
    for _ in range(passes):
        rnd.shuffle(order); moved = 0
        for i in order:
            a, k0 = sim.alloc[i], sim.cls[i]; best = (-0.1, None)
            runs_ok = near_runs(sim, i) if (move_runs and fixed[i] is None) else [a]
            for b in runs_ok:
                for k1 in range(L):
                    if b == a and k1 == k0: continue
                    dj = sim.delta(i, a, k0, b, k1)
                    if dj < best[0]: best = (dj, (b, k1))
            if best[1] is not None: sim.commit(i, a, k0, best[1][0], best[1][1]); moved += 1
        if moved == 0: break
    return list(sim.alloc), list(sim.cls), sim.J()

def seeded(prev_alloc, prev_cls, k_new, anchor, m):
    alloc, cls = list(prev_alloc), list(prev_cls)
    cand = [i for i in sorted(range(1, n), key=lambda i: Dl[anchor][i]) if not is_city[i] and fixed[i] is None][:m]
    for i in cand: alloc[i] = k_new
    seeds = [anchor]
    while len(seeds) < L: seeds.append(max(cand, key=lambda i: min(Dl[i][s_] for s_ in seeds)))
    for i in cand: cls[i] = min(range(L), key=lambda k: Dl[i][seeds[k]])
    return alloc, cls

def _task_k3(seed):
    sim = Sim(args.days, seed=3000 + seed); cls = init_classes(base_alloc, 3); sim.load(base_alloc, cls, 3)
    al, cl, J = local_search(sim, args.passes + 2, seed)
    return J, None, al, cl

def _task_new_run(payload):
    k, prev_alloc, prev_cls, anchor = payload
    alloc, cls = seeded(prev_alloc, prev_cls, k - 1, anchor, args.seed_size)
    sim = Sim(args.days, seed=4000 + k); sim.load(alloc, cls, k)
    al, cl, J = local_search(sim, args.passes, seed=k)
    return J, anchor, al, cl

def report(sim, label):
    st = sim.stats(); tot = sum(s["mean"] for s in st)
    print(f"{label}: total {tot/60:.2f} h/day | overtime {sum(s['over'] for s in st):.0f} min/day | any run over 12 h on {sim.p_any_over()*100:.0f}% of days | "
          + " | ".join(f"{run_name(r)} {s['mean']/60:.1f} h ({s['p_over']*100:.0f}%>12h, {s['members']} towns)" for r, s in enumerate(st)), flush=True)
    comps = components(sim.alloc, sim.R); cut = sim.cut_km()
    print(f"    compactness: border between runs {cut:,.0f} km | separate patches per run " + "/".join(str(c[0]) for c in comps) +
          " | share of towns in each run's main patch " + "/".join(f"{c[1]*100:.0f}%" for c in comps), flush=True)
    return {"total_min": tot, "overtime_min": sum(s["over"] for s in st), "p_any_over": sim.p_any_over(), "J_kappa2": sim.J(2.0, 0),
            "J_kappa10": sim.J(10.0, 0), "cut_km": cut, "components": comps, "runs": st}

if __name__ == "__main__":
    print(f"calibration: sample-day drive {sample_drive:.0f} min -> {sc:.1f} min per consignment; c = {c_dem*1000:.3f} per 1000 people/day; kappa = {KAPPA}")
    ctx = multiprocessing.get_context("fork"); pool = ProcessPoolExecutor(max_workers=args.workers, mp_context=ctx)
    val = Sim(args.val_days, seed=99); test = Sim(args.val_days, seed=123)
    results = {}; best = {}; alts = {}

    def choose(cands, k, keep, top=8):
        """Rank the best few candidates on the validation days; keep up to `keep` that differ in >= 6 localities."""
        cands = sorted(cands, key=lambda x: x[0])[:top]; scored = []
        for J, anchor, al, cl in cands:
            val.load(al, cl, k); scored.append((val.J(), anchor, al, cl)); _cache.clear()
        scored.sort(key=lambda x: x[0]); chosen = []
        for sc_ in scored:
            if all(sum(1 for i in range(1, n) if sc_[2][i] != o[2][i]) >= 6 for o in chosen): chosen.append(sc_)
            if len(chosen) == keep: break
        return chosen

    cur = Sim(args.days, seed=3000); cur_cls = init_classes(base_alloc, 3); cur.load(base_alloc, cur_cls, 3)
    _, cur_cls, _ = local_search(cur, args.passes + 2, 0, move_runs=False); _cache.clear()
    test.load(base_alloc, cur_cls, 3); results["current"] = report(test, "CURRENT allocation (3 runs)"); _cache.clear()

    t0 = time.time()
    chosen = choose(list(pool.map(_task_k3, range(args.starts3))), 3, keep=1)
    best[3] = (chosen[0][2], chosen[0][3]); alts[3] = chosen
    test.load(*best[3], 3); results["3_1"] = report(test, "BEST with 3 runs"); _cache.clear()
    print(f"  ({time.time()-t0:.0f}s)", flush=True)
    anchors = sorted((i for i in range(1, n) if not is_city[i] and fixed[i] is None), key=lambda i: -pop_eff[i])[:args.anchors]
    for k in range(4, args.max_runs + 1):
        t0 = time.time(); prev_alloc, prev_cls = best[k - 1]
        cands = list(pool.map(_task_new_run, [(k, prev_alloc, prev_cls, a) for a in anchors]))
        chosen = choose(cands, k, keep=3); best[k] = (chosen[0][2], chosen[0][3]); alts[k] = chosen
        for rank, (Jv, anchor, al, cl) in enumerate(chosen, 1):
            test.load(al, cl, k)
            results[f"{k}_{rank}"] = report(test, f"BEST{'' if rank == 1 else ' #' + str(rank)} with {k} runs (new run seeded at {nodes[anchor]['name']})"); _cache.clear()
        print(f"  ({time.time()-t0:.0f}s)", flush=True)
    pool.shutdown()

    cols = [(k, r) for k in sorted(alts) for r in range(len(alts[k]))]
    with open(DATA / f"more_runs_allocations{args.tag}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["name", "population", "px", "py", "current_run"] + sum([[f"run_{k}_{r+1}", f"day_class_{k}_{r+1}"] for k, r in cols], []))
        for i in range(1, n):
            w.writerow([nodes[i]["name"], nodes[i]["pop"], nodes[i]["px"], nodes[i]["py"], BASE_RUNS[base_alloc[i]]] +
                       sum([[run_name(alts[k][r][2][i]), alts[k][r][3][i] if not is_city[i] else "daily"] for k, r in cols], []))
    json.dump({"seeds": {f"{k}_{r+1}": nodes[alts[k][r][1]]["name"] if alts[k][r][1] else None for k, r in cols}, "results": results},
              open(DATA / f"more_runs_summary{args.tag}.json", "w"), indent=1, default=float)
    print("\nwrote data/more_runs_allocations%s.csv and data/more_runs_summary%s.json" % (args.tag, args.tag))
