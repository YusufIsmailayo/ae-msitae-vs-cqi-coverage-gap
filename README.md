# A&E 2025-26: MSitAE report tables vs CQI open data

I started from the footnote in NHS England Digital's *Hospital Accident & Emergency Activity 2025-26*, which says the MSitAE report tables "account for revisions to historic data and may therefore differ slightly" from the CQI open data. I tested whether that gap exists and what causes it.

## What I found

| Question | Result |
|---|---|
| Can I rebuild 27,976,025 attendances and 74.9288% from the monthly sitrep? | Yes, with zero residual, but only once booked-appointment attendances are included. Excluding them leaves a residual of -1,006,432 (-3.6%) and -0.56 pp. |
| Do CQI and the report tables differ because of revisions? | No evidence of it. For every provider-month CQI includes (1,838 of 1,838), CQI equals the final monthly sitrep exactly. |
| So where does the 836,365 (3.0%) gap come from? | CQI has no row for 41 providers (mostly urgent care and walk-in sites). The cause is not documented; CQI's organisation list looks like ECDS submitters. A code-prefix mismatch explains at most 207,626 of the 836,365. |
| Effect on four-hour performance | About 0.7 pp lower on CQI's provider set (74.22% vs 74.93%). This is my recalculation: CQI has no four-hour measure. |
| DNA counter-finding | Holds: appointments +2.92%, DNAs +0.09%, rate 5.42% (lowest in the 2015-16 to 2025-26 series), under three denominators. |

## Running it

`data/bronze` holds the files exactly as downloaded (SHA-256 in `data/bronze/manifest.parquet`). Run the notebooks in order from `notebooks/`:

1. `01_bronze_manifest` records hashes and source URLs.
2. `02_silver_tables` parses each file into typed Parquet and checks it against itself.
3. `03_reconciliation_gate` rebuilds the published annual figures and writes the residuals. It stops if the declared definition does not reconcile.
4. `04_coverage_gap` measures the gap, identifies the omitted providers and draws the chart.
5. `05_dna_rebuild` rebuilds the outpatient DNA claims.

Shared parsers are in `src/common.py`; `src/build_notebooks.py` regenerates the notebooks.

## Limits

- The monthly files I used are the final published versions. I have not tested the original provisional releases, so I cannot say CQI is never revised.
- The report tables say planned attendances are excluded, yet the figures only reconcile with booked attendances in. "Booked" may not mean "planned"; I have not asked NHS England.
- The DNA rate's denominator includes cancellations. The rate falls under every denominator I tried, but that is not proof people attend more reliably.
