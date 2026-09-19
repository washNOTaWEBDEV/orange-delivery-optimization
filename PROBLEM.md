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

All drivers may be assumed to begin and end at the depot each day. A van is never loaded twice in a day, so each driver's day is a single trip out from the depot and back. The 12-hour limit and the total delivery time cover the driving and delivering from leaving the depot to returning, including the long drive to and from the region. They do not include end-of-day loading at the depot or breaks. A van never fills up, by count, weight or size, before the 12 hours are used, so van capacity is ignored.

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

## 5. Current runs (from the map screenshot)

The current territories are drawn in Google My Maps as semi-transparent polygons. Many more towns exist than are labelled. Extents are rough readings of the picture, and the drawn polygons overlap along some borders.

| Run | Polygon | Roughly covers |
|---|---|---|
| Hamilton | purple, very large | Hamilton and the north-west: from the South Australian border east to about Lismore, north to about the Grampians and Horsham, south to roughly Byaduk, Penshurst, Mortlake and Hawkesdale. Labelled towns inside include Coleraine, Casterton, Balmoral, Dunkeld, Glenthompson, Caramut, Hexham, Woorndoo and Lake Bolac. |
| Portland | green, south-west | From the SA border (Nelson) through Portland, Cape Bridgewater, Heywood, Narrawong and Tyrendarra to Port Fairy; north-east to Condah, Macarthur and Hawkesdale. |
| Warrnambool | blue, south-west coast | Koroit and Tower Hill through Warrnambool, Woolsthorpe, Grassmere, Nullawarre, Timboon and Simpson to Port Campbell and Princetown, with a lobe reaching up to Hawkesdale. Currently split between two drivers (the split line was drawn on the original map); splitting is ignored for now. |

- Overlaps: Hamilton and Portland along a band from about Condah and Macarthur to Hawkesdale; Portland and Warrnambool around Port Fairy and Hawkesdale; Hamilton and Warrnambool slightly along Warrnambool's northern edge. **Hawkesdale** sits where all three polygons overlap.
- The other polygons on the map are, per the final summary, unrelated runs, and are ignored for now: a pale yellow one between the eastern tip of the Hamilton polygon and Geelong (presumably Golden Plains, which the chat places north-east or east of the Hamilton run), and small ones at Geelong, Lara/Corio, Torquay/Anglesea and Colac.
- A small black polygon around Noorat, Terang, Camperdown and Cobden, on the north-eastern edge of the Warrnambool polygon, is unexplained. It may be the Warrnambool split or a separate small run; it is ignored for now along with the other smaller runs.

## 6. Data

**Available**
- Every driver's run sheets, including the town of each consignment. Access is described as unlimited for "the places for which drivers really load". Exporting them is manual and slow (weak internet connection in the warehouse).
- One sample run sheet export: one driver's run (the Warrnambool run) on one particular day, 36 consignments. Only the receiver's location is relevant to this problem, so the working copy keeps only the receiver's location fields and drops everything else, including customer, sender and receiver names. The file is kept locally and out of version control. The export had no date, run name, driver or timing fields.
- Google Maps, personal experience, and other drivers' experience for geography and timings.
- Population data, for example the Victoria population map based on the 2021 Census (https://mangomap.com/franchise-demo/maps/88276/Victoria-Population-Map). The problem owner says population is highly correlated with delivery volume, so it can be treated as a good heuristic for volume for now. The map shows how strongly the three cities dominate the volume. The problem owner can supply population data if it is needed.

**Thin or missing**
- Durations of runs: "very little data on the length of time of runs". The problem owner will provide some real durations. So far there is one: the sample run above took 11 hours 43 minutes in total, including breaks, which the 12-hour limit excludes.

**Sensitivity**
- The problem owner first believed per-town consignment counts over time were not accessible, and that the boss would not like them being accessed. Access was later found to exist. Whether the company is comfortable with the data being used outside the workplace is not settled, so treat raw run sheets as confidential and keep them out of version control.

## 7. Open points

- **Waits.** How irregular arrivals should be modelled (for example, average rates from history) is not stated.
- **Scope.** The full list of towns in the three runs is not given (it can be derived from the run sheets).
- **Run sheet coverage.** The sample export has no date, run name, driver or timing fields, so each sheet's run and date, and how long that day took, have to be supplied separately.
- **Sample run timing.** The length of the breaks inside the sample run's 11 hours 43 minutes is not stated, so its length under the 12-hour measure (which excludes breaks) is not known.
