# First attempt at optimizing the runs

Written for: the two people working on the problem. Not committed to the repository.

## Result in one paragraph

Under the stated rules (three runs, one driver per run, 12-hour limit, 2-day wait for every town except the three cities) and with demand calibrated on the one sample day, the model says the current Hamilton run is over 12 hours on about 56% of days. Moving Hamilton's south-west border towns to the Portland run brings that down to 27-34% of days for about 23-25 minutes less total driving per day (roughly 100 hours a year). Portland's run gets longer in exchange. The three best allocations found are in `allocation_1.png`, `allocation_2.png` and `allocation_3.png`. Treat the differences between them as within model noise: the calibration rests on one sample day.

## The three best allocations (untouched test days)

| | All three runs | Hamilton over 12 h | Portland over 12 h | Warrnambool over 12 h | Localities moved |
|---|---|---|---|---|---|
| Current | 34.6 h/day | 56% of days | 4% | 20% | none |
| Allocation 1 | 34.3 h/day | 34% | 26% | 18% | 27 (3,600 people) |
| Allocation 2 | 34.2 h/day | 27% | 38% | 16% | 30 (4,900 people) |
| Allocation 3 | 34.3 h/day | 28% | 34% | 16% | 29 (4,400 people) |

Found by 12 independent local searches on different simulated days, plus the earlier candidates, ranked on a second set of days, and reported on a third set. Chosen to differ from each other in at least 5 localities.

**Moves that hold up.** 16 localities were chosen by at least 3 of 4 settings (demand as calibrated, -30%, +30%, and no overtime penalty): to Portland from Hamilton Macarthur, Hawkesdale, Branxholme, Minhamite, Condah, Wallacedale, Myamyn, Gazette, Warrabkook, Breakaway Creek, Hotspur, Gerrigerrup and Knebsworth; to Portland from Warrnambool Kirkstall and Toolong; to Warrnambool from Hamilton Ellerslie. That package alone saves about 10 minutes a day and lowers Hamilton's over-12-hour days from 56% to 44% (`data/robust_moves.csv`). Larger moves such as Casterton (1,673 people) to Portland appear only under some settings.

**Macarthur and Hawkesdale** (free to assign): Portland is best by about 4-6 minutes a day over the alternatives, close to a tie.

## Time saved versus the current allocation

Both allocations are simulated on the same 3,000 untouched days, so each difference is paired. Every allocation's rotation days are re-optimised at each demand level. All the saving is driving, because time spent on consignments does not change. Overtime means time over 12 hours. Years assume about 250 working days.

At demand as calibrated (current allocation: 34.6 h/day of van time, 77 minutes/day of overtime):

| | Van time saved | Hamilton run | Portland run | Warrnambool run | Overtime saved | Per year |
|---|---|---|---|---|---|---|
| Allocation 1 | 25 min/day (+-4), 1.2% | 64 min shorter | 42 min longer | about the same | 45 min/day | about 100 h |
| Allocation 2 | 24 min/day (+-4), 1.1% | 80 min shorter | 62 min longer | about the same | 40 min/day | about 100 h |
| Allocation 3 | 23 min/day (+-4), 1.1% | 76 min shorter | 57 min longer | about the same | 41 min/day | about 95 h |

If demand is 30% lower than calibrated, the saving falls to 5-7 min/day and there is little overtime to remove (12 min/day). If demand is 30% higher, the saving is 8-10 min/day and overtime falls by about 40 of 177 min/day. The full table is in `data/allocation_savings.csv`.

## Letting the number of runs vary

The number of runs was freed (3 to 5). Runs 1-3 keep their cities; an extra run has no city and is a further driver leaving Geelong on the days it has stops. Because a fourth run costs a whole extra round trip, the 12-hour limit is weighted heavily here (a minute over 12 hours counts as 10 minutes of van time). Numbers are on untouched simulated days at the calibrated demand, and are only comparable within this table.

| | Van time | Time over 12 h | Days with any run over 12 h | Hamilton / Portland / Warrnambool over 12 h | Fourth run |
|---|---|---|---|---|---|
| Current allocation | 34.4 h/day | 52 min/day | 71% | 63% / 4% / 19% | none |
| Best with 3 runs | 34.4 h/day | 34 min/day | 62% | 33% / 32% / 16% | none |
| 4 runs, option 1 | 36.5 h/day | 18 min/day | 39% | 23% / 15% / 5% | 27 towns, 12,000 people |
| 4 runs, option 2 | 36.4 h/day | 18 min/day | 41% | 23% / 17% / 5% | 31 towns, 11,400 people |
| 4 runs, option 3 | 36.7 h/day | 18 min/day | 40% | 22% / 16% / 6% | 33 towns, 8,200 people |
| 5 runs | 36.3-36.4 h/day | 17-18 min/day | 37-38% | about the same as 4 runs | fifth run stays empty |

- **A fifth run is never worth opening.** In all three options the search left it empty.
- **A fourth run is a poor trade.** It removes about 16 minutes of overtime a day compared with the best three-run allocation, but adds 2.0-2.3 van-hours a day. That is about 8 minutes of extra driving for every minute of overtime removed, so it only pays if a minute over 12 hours is worth more than about 8 minutes of ordinary van time.
- **The fourth run works one day in three.** In each option it makes a full trip of about 10-11 hours on its one day and none on the other two, so it behaves like a part-time driver. It takes the south-west coast corridor (Port Fairy, Dennington, Allansford, Koroit, Kirkstall and neighbours) plus scattered small towns elsewhere.
- **Its territory is patchy.** The model does not penalise a run whose towns are not one connected area, so the fourth run in the images is fragmented. That may be impractical for warehouse sorting; a compactness rule could be added.
- **Overtime never disappears.** Even with four runs some run is over 12 hours on about 40% of days, because daily volumes vary. Removing that would need spare capacity on heavy days, such as a second driver only when a run is full. That is the splitting you asked me to ignore for now, and it would likely cost far less than a permanent fourth run.

Images: `allocation_4runs_1.png`, `allocation_4runs_2.png`, `allocation_4runs_3.png`, and `allocation_3runs_1.png` for the best three-run allocation at the same overtime weight. Data: `data/more_runs_allocations.csv`, `data/more_runs_summary.json`. Code: `scripts/optimize_more_runs.py`, `scripts/allocation_images_more.py`.

## Adding a compactness preference

**What the "penalty" is.** The search scores each allocation with one number, its total van minutes per day. The compactness penalty adds a small cost for every kilometre of border between two localities that are in different runs. A run made of scattered patches has a lot of border, so it scores worse; one connected area has little. It is a preference, not a rule: a large enough time saving can still justify a patchy run. The van hours reported below do not include the penalty. Border lengths come from the boundary polygons (594 neighbouring pairs, 6,071 km of border in all). Today's allocation has 406 km of border between runs, and Warrnambool is in 2 patches.

Three strengths were tried, in minutes of van time per day per kilometre of border. Same demand and overtime weight as the table above.

| | Runs | Van time | Time over 12 h | Border between runs | Patches per run |
|---|---|---|---|---|---|
| Current allocation | 3 | 34.4 h/day | 52 min/day | 406 km | 1 / 1 / 2 |
| No compactness preference | 3 | 34.4 h | 34 min | 846 km | 4 / 3 / 3 |
| No compactness preference | 4 | 36.5 h | 18 min | 1,587 km | 7 / 1 / 5, and 9 for the fourth run |
| Light (0.1) | 3 | 34.4 h | 34 min | 457 km | 1 / 1 / 2 |
| Light (0.1) | 4, fourth run in the west | 36.6 h | 17 min | 479 km | 1 / 1 / 2 / 1 |
| Moderate (0.4) | 3 | 34.2 h | 37 min | 346 km | 1 / 1 / 2 |
| Moderate (0.4) | 4, fourth run in the north | 36.6 h | 18 min | 442 km | 2 / 1 / 2 / 1 |
| Strong (1.5) | 3 | 34.4 h | 46 min | 364 km | 1 / 1 / 2 |
| Strong (1.5) | 4 | no fourth run opens | | | |

- **Compactness is cheap.** At the moderate strength the best three-run allocation is more compact than today's (346 km against 406 km) and no worse on time: 34.2 h/day against 34.4 h, and 37 against 52 minutes over 12 hours. Only 20 localities change run, all along the Hamilton-Portland border. This is the allocation to start from: `compact_mu0.4_3runs_1.png`.
- **The earlier "best" allocations were patchy.** Without the preference the three-run search doubled the border to 846 km, and the four-run one scattered the fourth run over 9 patches.
- **A fourth run is still a poor trade,** but it now takes a compact sector. At the light strength it is the west of Hamilton's territory (Casterton, Coleraine, Merino, Digby, Strathdownie: 32 towns, 4,800 people). At the moderate strength it is the north around Haven and Balmoral (17 towns, 3,100 people). Either way it works one day in three, adds about 2.2 van-hours a day, and removes only about 20 minutes of overtime.
- **At the strong setting** the allocation stays close to today's and no extra run is worth opening.

Images: `compact_mu0.4_3runs_1.png`, `compact_mu0.1_4runs_1.png`, `compact_mu0.4_4runs_1.png`. Data: `data/more_runs_allocations_mu0.1.csv`, `_mu0.4.csv` and `_mu1.5.csv`, with matching summaries. Code: `scripts/build_adjacency.py`, and `scripts/optimize_more_runs.py --mu`.

## Three runs again, with the compactness preference

The number of runs is fixed at three again, and the moderate compactness preference (0.4 minutes per km of border) is kept. Twelve independent searches, ranked on one set of simulated days and reported on another untouched set; savings are paired against the current allocation on the same days. Overtime is weighted 10 times here, as in the sections above.

| | Van time saved | Time over 12 h saved | Hamilton / Portland / Warrnambool over 12 h | Border between runs | Localities moved |
|---|---|---|---|---|---|
| Current allocation | | | 63% / 4% / 19% of days | 406 km | |
| Compact 1 | 13 min/day (+-4), 0.6%, about 53 h/year | 17 min/day | 42% / 24% / 11% | 349 km | 21 (3,100 people) |
| Compact 2 | 10 min/day (+-3), about 40 h/year | 14 min/day | 28% / 45% / 12% | 349 km | 30 (5,300 people) |
| Compact 3 | 4 min/day (+-3), about 15 h/year | 15 min/day | 30% / 42% / 15% | 368 km | 28 (4,700 people) |

- **All three keep every run one connected area** (1 patch each, and Warrnambool 2 as today) with less border than today's 406 km.
- **The same moves, mostly.** Hamilton's south-west border towns go to Portland (Macarthur, Hawkesdale, Dartmoor, Strathdownie), Kirkstall, Crossley and Killarney go from Warrnambool to Portland, and Ellerslie goes from Hamilton to Warrnambool. Compact 2 and 3 also move Casterton (1,673 people) to Portland, which is what lowers Hamilton's over-12-hour days and raises Portland's.
- **Compact 1 is the gentlest change** (21 localities, 3,100 people) and the best on van time. Compact 2 trades a longer Portland day for a much shorter Hamilton one.
- **Why the saving is smaller than in the first table.** These searches weight overtime 10 times rather than 2, so they give up some van time to remove overtime, and they are compact. The compactness preference itself did not cost anything measurable: without it the three-run search found 34.4 h/day, with it 34.2 h/day.

Images: `compact3_3runs_1.png`, `compact3_3runs_2.png`, `compact3_3runs_3.png`. Data: `data/more_runs_allocations_3runs_mu0.4.csv` and its summary. Code: `scripts/allocation_savings_more.py`.

## How it works

- **Demand.** A locality generates consignments at c x population per day, with c = 0.73 per 1,000 people, chosen so the Warrnambool run averages the 36 consignments of the sample day. Horsham is treated as rarely appearing.
- **Time.** Road times between 232 localities and the depot come from a public routing service (OpenStreetMap data). Time per consignment is 7.5 minutes (stops, in-town driving and breaks), chosen so the sample day comes to 11 h 43 min.
- **Wait rule.** A 2-day wait means each town is visited on one day of a 3-day rotation, when consignments are waiting. The search chooses each town's run and its rotation day together.
- **Objective.** Minimise total minutes per day plus twice the minutes over 12 hours.
- **Population** comes from the 2021 Census; run outlines are read from the map screenshot (the KML was not used).

## Things to keep in mind

- One sample day sets the demand level and the time per consignment. Hamilton and Portland volumes are extrapolated from population. The claim that Hamilton is over 12 hours on more than half of days is probably too pessimistic until it is checked against real Hamilton run times.
- Even a 4-day wait only brings Hamilton's average to about 12 hours: the trip from Geelong to Hamilton alone is 3 h 10 min each way. The stated 2-day wait is not the main cause.
- Membership near the outlines is approximate (locality centres, about 2 km error).
- The Cobden/Camperdown/Terang run, Golden Plains and the other smaller runs are excluded, as instructed. Splitting a run between drivers is ignored.

## Files to look at

| File | What it is |
|---|---|
| `allocation_1.png`, `allocation_2.png`, `allocation_3.png` | The three best allocations, one image each |
| `population_density_map.png` | Population density by locality with the current outlines |
| `proposed_reallocation_map.png` | Robust moves (solid) and assumption-dependent moves (hollow) |
| `data/top3_allocations.csv` | Every locality's run in each allocation, with its rotation day |
| `data/robust_moves.csv` | The 16 moves that hold up |
| `data/borderline_localities_from_image.csv` | Localities within about 3 km of an outline |
| `data/localities_by_run_from_image.csv` | Localities inside each outline, with population |
| `data/logs/` | Full output of each optimization run |
| `allocation_4runs_1.png`, `allocation_4runs_2.png`, `allocation_4runs_3.png`, `allocation_3runs_1.png` | Allocations when the number of runs is free |
| `compact_mu0.4_3runs_1.png`, `compact_mu0.1_4runs_1.png`, `compact_mu0.4_4runs_1.png` | Allocations with the compactness preference |
| `compact3_3runs_1.png`, `compact3_3runs_2.png`, `compact3_3runs_3.png` | Best three allocations with exactly three runs and the compactness preference |
| `scripts/` | The code: `allocation_savings_more.py`,  `build_adjacency.py`,  `density_map.py`, `classify_localities.py`, `route_times.py`, `optimize_runs.py`, `optimize_more_runs.py`, `allocation_images.py`, `allocation_images_more.py`, `reallocation_map.py`, `allocation_savings.py` |

## What would improve this most

1. Run sheets and total times for a few Hamilton and Portland days (run name, date, total time, suburbs), so demand and time per consignment are calibrated on more than one day.
2. The real town-to-run list for the borderline localities.
