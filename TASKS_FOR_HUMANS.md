# Tasks for humans

Real-world measurements that would most improve the run allocation work. The model so far rests on one sample day, population figures, and road times from a mapping service. Everything below replaces a guess with a measurement.

## If you can only do one thing

Get **timed delivery records for about 10 working days on each of the Hamilton, Portland and Warrnambool runs** (task 1), with the **daily log** (task 3). That alone would tell us how long a stop really takes, how far off the road-time estimates are, and whether Hamilton really runs over 12 hours as often as the model says.

## How to send it

- **Suburb only.** No customer names, no street addresses, no consignment numbers. We only need the suburb of each stop.
- A spreadsheet or CSV is fine. One file per run per day is fine. Name files like `runlog_hamilton_2026-10-05.csv`.
- Use driver codes (D1, D2, ...), not names.
- Keep the files in the local project folder. **Do not put them on GitHub**: the repository is public.
- If something is not recorded anywhere, say so. "Not available" is a useful answer.

## Measurements to collect

### 1. Timed deliveries (most valuable)

For each consignment delivered on a run: **date, run, driver code, suburb, time of the delivery scan, and whether it was a delivery or a pickup.** If the handheld or software records scan times, export them. If not, the driver notes arrival and departure time at each stop (on paper or a phone note is fine).

- **How much:** at least 10 working days per run, 30 driver-days in all. Include one busy week and one quiet week.
- **Why:** it gives the real time per stop and the real driving time between stops. Today the model assumes 7.5 minutes per consignment (stops, in-town driving and breaks lumped together), calibrated on a single day.

### 2. The route software's plan and what actually happened

For the same days: the **planned stop order, planned drive time and distance**, then the **actual depart and return times and the total kilometres** (odometer). A screenshot of the software's route summary is enough.

- **Why:** lets us check our routing against the drivers' software and against reality. We built routes ourselves from road times and never compared them with a real route.

### 3. Daily run log (5 minutes at the end of each day)

One row per run per day, with these columns:

```
date, run, driver_code, left_depot_HH:MM, back_at_depot_HH:MM,
break_start_HH:MM, break_end_HH:MM (repeat if more than one),
end_of_day_loading_minutes, consignments_delivered, number_of_stops,
suburbs_visited, consignments_left_behind_by_suburb, second_driver_used (yes/no),
notes (road closures, weather, anything unusual)
```

- **How much:** the same days as task 1.
- **Why:** total time, break time and loading time are what the 12-hour limit is about. We only have them for one day.

### 4. What is waiting at the depot

Before loading, for each run and each of the same days: the **number of consignments waiting per suburb**, and **the date each arrived at the depot** (the depot's receipt scan, if one exists). Also whether a "received at depot" date can be exported at all.

- **Why:** the run sheets only show what drivers took, not what was available or how long parcels waited. This is the direct check on the two biggest assumptions: that volume follows population, and how long small towns really wait.

## Questions to ask a driver or the warehouse lead (about 30 minutes)

5. **Which run does each town belong to?** The warehouse sort rules by suburb or postcode, for every town in the three runs. Especially: Toolong, Port Fairy, Kirkstall, Killarney, Crossley, Mortlake, Hawkesdale, Macarthur, Dartmoor, Casterton, Strathdownie and Horsham. Also which towns belong to the smaller runs (Cobden/Camperdown/Terang, Colac, Golden Plains) and how the Warrnambool split is divided.
6. **How do drivers choose which small towns to visit on a given day?** A fixed weekday rotation, or whatever has built up? What is the longest a parcel actually sits in practice, and what does the boss accept? Are any towns visited every day besides the three cities?
7. **Horsham.** About how many Horsham consignments a month, and what happens on a day one appears (who goes, how long it adds)?
8. **When a run is too big.** How often is a second driver added, on which runs, and what triggers it? How is the run divided that day (by area or by town)? What happens if a run would pass 12 hours and no second driver is free?
9. **The rules behind the numbers.** Where does the 12-hour limit come from? Are breaks mandatory, how long, and when? What time do drivers start? How long does end-of-day loading take? Do any deliveries have time windows (shops that close at 5, for example)?
10. **Routes and depot.** Which roads do drivers take from Geelong to each region (for example Princes Highway or Hamilton Highway)? Where in Geelong is the depot? Do vans start from the depot or go home with the driver?
11. **Pickups.** Do runs include collections as well as deliveries? Roughly how many, and where?
12. **Busy periods.** Which weeks are the busiest (Christmas, sales, end of financial year), by roughly how much? How do Mondays compare with Fridays?

## Nice to have

13. **A longer history:** 6-12 months of consignment counts per suburb per day per run (counts only). This would replace the population guess with real per-town volumes. If this is sensitive, weekly counts per suburb are enough.
14. **Failed and repeat deliveries:** roughly what share of consignments need a second attempt, and in which towns.
15. **A population check:** consignments per week for about 30 towns of different sizes, to see how well population predicts volume. We already know Horsham and one tiny locality break the pattern.

## What we will do with it

| Task | What it replaces | What it could change |
|---|---|---|
| 1, 2, 3 | 7.5 minutes per consignment; road times from a mapping service | How long each run really takes, and so which runs are over 12 hours |
| 4, 13, 15 | Volume proportional to population | Which towns matter, and how demand splits between runs |
| 5 | Run membership read from a screenshot | The starting allocation, and which towns are really borderline |
| 6, 12 | A 3-day rotation for the 2-day wait | How often each town is visited |
| 7, 8, 9, 11 | Horsham as a rare visit; no second drivers; a fixed 12-hour limit | Whether a day-by-day second driver beats moving towns between runs |
| 10 | Depot placed at the middle of Geelong | Every run's driving time to and from the region |

With this data the allocations can be rerun on measured numbers and the estimated time savings restated with real error margins.
