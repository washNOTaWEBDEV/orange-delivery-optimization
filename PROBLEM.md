# Delivery run allocation: problem summary

Compiled 2026-09-19 from three sources: a short final written summary of the problem (the authoritative statement), an earlier chat between the two people working on it (6-12 Sep 2026), and a screenshot of the current run map. Where the chat disagreed with the final summary, the summary was followed. The facts come from a driver's first-hand experience, not from company documents. This file is meant to be a self-contained statement of the problem for a solver (human or LLM). It states the problem only and proposes no solution.

## 1. The problem

Deliveries enter a warehouse irregularly. There are several drivers. Deliveries are sorted into distinct physical areas of the warehouse, and each area is a **run**. A driver is told which run they will do each day and must only pick deliveries that belong to that run.

The one depot is in Geelong (Victoria, Australia), and each driver begins and ends their day there. There are three runs, each loosely based around one of the three cities in western Victoria: **Portland, Hamilton and Warrnambool**. Which town is allocated to which run is already established, but there is thought to be room for optimization in that allocation. The routes themselves are already optimized: drivers are provided with route-optimization software, choose their packages for the day, scan them into the software, and it provides an optimal route. A driver can be assumed to take an efficient route once the day's packages are chosen. The question is the allocation of towns to runs, not the optimization of deliveries once loaded.

**Question: which towns should belong to which run, so that total delivery time across drivers is as low as possible?**

**Scope of the answer:** if a whole reallocation seems doable, despite the little data available now, try it. Otherwise start from the currently defined runs and consider reallocating borderline towns (section 4 gives Hawkesdale as an example).

## 2. Constraints and objective

| # | Constraint |
|---|---|
| 1 | Each town belongs to exactly one run. |
| 2 | Deliveries bound for any of the three cities must be loaded on the day they arrive, to be delivered the next day. |
| 3 | Select high-volume towns may wait 1 day before being loaded for delivery. |
| 4 | Every other town may wait 2 days before being loaded for delivery. |
| 5 | Drivers must not spend more than 12 hours on any one run. |

**Objective:** the lowest total delivery time across drivers. It does not matter if one run is much longer than the others, as long as each is within 12 hours.

These are hard requirements for now. The number of runs (three) and the rule that a driver only picks deliveries belonging to their assigned run are fixed on the same terms. The problem owner may change any of them later.

Splitting a run between two drivers is ignored for now, so each run is done by one driver per day and the 12-hour limit applies to the run as a whole. The smaller runs shown on the map (section 5) are also ignored for now. For now, every town other than the three cities is assumed to have a 2-day wait (constraint 3 is not applied), since there is little data on which towns are high-volume.

All drivers may be assumed to begin and end at the depot each day. A van is never loaded twice in a day, so each driver's day is a single trip out from the depot and back. The 12-hour limit and the total delivery time cover the time from leaving the depot to returning, including the long drive to and from the region and any breaks. They do not include end-of-day loading at the depot. A van never fills up, by count, weight or size, before the 12 hours are used, so van capacity is ignored.

## 3. Terms

- **Run**: a distinct physical area of the warehouse into which the deliveries for a fixed set of towns are sorted. It is also the territory a driver covers that day: an established territory that conventionally takes about a day's work.
- **Consignment**: a package (approximately); the unit of delivery.
- **Run sheet**: a driver's list of the consignments taken on a trip. It records the town of each.
- **Depot / warehouse**: the same place; the words are used interchangeably.
- **Working day**: a weekday that is not a public holiday.
- **Wait**: the working days a consignment sits in the warehouse before being loaded (constraints 3 and 4). Weekends and public holidays do not count toward a wait.

## 4. Background from the chat

The chat adds this context. None of it overrides the final summary.

**Runs and the warehouse**
- Runs are established and are not redrawn from day to day or week to week: they "shouldn't change probably at all". An answer is therefore a standing allocation, not a daily plan.
- Runs are kept from overlapping because of warehouse logistics: each consignment is sorted into one run in the physical warehouse, and a driver assigned to a run scans what they will take on that run and loads it into the van.
- Drivers usually do a different run each day. The rotation evens out differences in difficulty between runs.
- Within their run, drivers choose which packages to take. The chat calls this "somewhat free", guided by what the boss would be upset about: they cannot take too few consignments, and cannot leave out-of-the-way consignments behind too aggressively or too many times in a row.
- Each of the three runs includes its namesake city.
- A run with a lot of volume can be shared by two drivers, by splitting it into two pseudo-runs. The Warrnambool run is currently split this way. Splitting is ignored for now (section 2).

**Depot and travel**
- There is only one depot. A depot further west has been wondered about, but volume may not justify it.
- Drivers load the next day's van at the depot at the end of the day.
- Most runs are very far from Geelong, and everyone lives close to the depot.

**What was wanted from an answer**
- "Reasoning that beats intuition." A full mathematical optimization that also handled varying driver availability, varying volume per area and deliveries sitting in the warehouse for a while was judged too hard and dropped.
- A way to decide which run a given town belongs to, and to calculate which run it would add the least total delivery time to. The chat said a way to evaluate select controversial towns would be enough; the final summary asks for the full allocation. See the scope of the answer in section 1.
- A method the problem owner can follow and reuse. They treat mathematics as "a tool to understand things I care about" and are willing to learn what the method needs.

**Example town: Hawkesdale.** Which run should it belong to? It is the only town that has been in all three runs.

## 5. Current runs (from the run map)

The current territories are drawn in Google My Maps and exported as a KML file, Main.kml, which holds ten named polygons. The file is not committed to the repository. Its polygons give the exact boundaries; the extents below are rough, and the areas are computed from it.

| Run | Colour | Area | Roughly covers |
|---|---|---|---|
| Hamilton | purple | about 16,900 km² | Hamilton and the north-west: from the South Australian border east past Lismore to the edge of the Golden Plains polygon, north to about Horsham and the Grampians, south to roughly Byaduk, Penshurst, Mortlake and Hawkesdale. Labelled towns inside include Coleraine, Casterton, Balmoral, Dunkeld, Glenthompson, Caramut, Hexham, Woorndoo and Lake Bolac. |
| Portland | green | about 4,450 km² | From the SA border (Nelson) through Portland, Cape Bridgewater, Heywood, Narrawong and Tyrendarra to Port Fairy; north-east to Condah, Macarthur and Hawkesdale. |
| Warrnambool | blue | about 2,960 km² | Koroit and Tower Hill through Warrnambool, Woolsthorpe, Grassmere, Nullawarre, Timboon and Simpson to Port Campbell and Princetown, with a lobe reaching up to Hawkesdale. The run is currently split between two drivers on high-volume days; splitting is ignored for now. |

- **Overlaps.** The three polygons overlap: Hamilton and Portland by about 1,170 km², Portland and Warrnambool by about 135 km², Hamilton and Warrnambool by about 70 km². The map alone therefore does not say which run a town in those zones belongs to. **Hawkesdale** (approximate coordinates) lies inside all three polygons.
- **Other polygons.** The KML names seven more runs. The final summary calls them unrelated, and they are ignored for now: Golden Plains (about 1,350 km², east of the Hamilton polygon, overlapping it by about 50 km²), "Cobden, Camperdown, Terang" (about 310 km², on the north-eastern edge of the Warrnambool polygon), Colac, Otways, Central Geelong, Northern Geelong and Southern Geelong.
- **The split.** The KML has no split line for the Warrnambool run. Whether the "Cobden, Camperdown, Terang" polygon is the second half of that split or a separate run is not stated.

## 6. Data

**Available**
- Every driver's run sheets, including the town of each consignment. Access is described as unlimited for "the places for which drivers really load". Exporting them is manual and slow (weak internet connection in the warehouse).
- One sample run sheet export: one driver's run (from its towns, the Warrnambool run) on one particular day, 36 consignments. Only the receiver's location is relevant to this problem, so the working copy keeps only the receiver's location fields and drops everything else, including customer, sender and receiver names. The file is kept locally and out of version control. The export had no date, run name, driver or timing fields.
- The current run boundaries as a KML file, Main.kml (see section 5).
- A working list, kept locally, of the 220 localities whose centres fall inside a run outline on the map screenshot, with their census populations (approximate near the outlines; the KML was not used). By population, localities inside only the Warrnambool outline total about 48,300 people, Hamilton about 42,300 and Portland about 20,900, with about 300 in localities in overlaps. A further 65 localities lie within about 3 km of an outline, so their run is uncertain.
- Google Maps, personal experience, and other drivers' experience for geography and timings.
- Population data. The problem owner says population is highly correlated with delivery volume, so it can be treated as a good heuristic for volume for now. The 2021 Census General Community Profile for Victoria has been supplied: total persons by locality (suburbs and localities) are in table G01, column Tot_P_P, for 2,944 localities summing to about 6.49 million. A compact extract (locality name, total persons, area) is kept locally and out of version control. Locality centre coordinates were fetched from public ABS boundary data. In very small localities the count is a weak proxy: one locality on the sample run has no recorded residents. A Victoria population map based on the same census (https://mangomap.com/franchise-demo/maps/88276/Victoria-Population-Map) shows how strongly the three cities dominate the volume.

**Thin or missing**
- Durations of runs: "very little data on the length of time of runs". The problem owner will provide some real durations. So far there is one: the sample run above took 11 hours 43 minutes in total, including breaks, which count toward the 12-hour limit. That is 17 minutes under the limit.

**Sensitivity**
- The problem owner first believed per-town consignment counts over time were not accessible, and that the boss would not like them being accessed. Access was later found to exist. Whether the company is comfortable with the data being used outside the workplace is not settled, so treat raw run sheets as confidential and keep them out of version control.

## 7. Open points

- **Waits.** How irregular arrivals should be modelled (for example, average rates from history) is not stated.
- **Scope.** The full list of towns in the three runs is not given. Because the map polygons overlap, it cannot be read from the map alone (it can be partly derived from run sheets).
- **Cobden, Camperdown, Terang.** Whether this polygon is a separate run or the second half of the Warrnambool split is not stated. The answer decides whether its towns are in scope.
- **Town-to-run allocation.** The current allocation is only approximated from the outlines on the screenshot, using locality centres, which can sit several kilometres from the town itself. The real allocation of the uncertain localities near the outlines is not known.
- **Run sheet coverage.** The sample export has no date, run name, driver or timing fields, so each sheet's run and date, and how long that day took, have to be supplied separately.
