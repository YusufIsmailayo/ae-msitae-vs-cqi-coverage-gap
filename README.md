# A&E 2025-26: MSitAE report tables vs CQI open data

I started from the footnote in NHS England Digital's *Hospital Accident & Emergency Activity 2025-26*, which says the MSitAE report tables "account for revisions to historic data and may therefore differ slightly" from the CQI open data. I tested whether that gap exists and what causes it.

## What I found

| Question | Result |
|---|---|
| Can I rebuild 27,976,025 attendances and 74.9288% from the monthly sitrep? | Yes, with zero residual, but only once booked-appointment attendances are included. Excluding them leaves a residual of -1,006,432 (-3.6%) and -0.56 pp. |
| Do CQI and the report tables differ because of revisions? | No evidence of it. For every provider-month CQI includes (1,838 of 1,838), CQI equals the final monthly sitrep exactly. Revisions do exist but are small (see next row), and CQI carries the revised values, so it is not a frozen snapshot. |
| How big are the revisions? | For the six months I could retrieve first-published files for (Apr, May, Jun, Oct, Nov, Dec 2025), final totals differ from first-published by -0.04% to +0.15% (1 to 3 providers a month), moving four-hour performance by at most 0.04 pp. All 9 revised providers that CQI includes carry the final value in CQI, none the provisional one. |
| So where does the 836,365 (3.0%) gap come from? | CQI has no row for 41 providers (mostly urgent care and walk-in sites). The cause is not documented; CQI's organisation list looks like ECDS submitters. A code-prefix mismatch explains at most 207,626 of the 836,365. |
| Effect on four-hour performance | About 0.7 pp lower on CQI's provider set (74.22% vs 74.93%). This is my recalculation: CQI has no four-hour measure. |
| 1.85x deprivation ratio | Verified: 62,284 vs 33,667 attendances per 100,000 = 1.8500, rebuilt from counts too. It is an ECDS figure (26.64m attendances, 2.6% with no IMD), not an MSitAE one. About 0.02 of the fall from 1.89 in 2024/25 is a population-denominator update. |
| DNA counter-finding | Holds: appointments +2.92%, DNAs +0.09%, rate 5.42% (lowest in the 2015-16 to 2025-26 series), under three denominators. |

## Running it

`data/bronze` holds the files exactly as downloaded (SHA-256 and source URL in `data/bronze/manifest.parquet`). The one exception is the 13.6 MB ECDS National Report Tables workbook, which is gitignored: download it from its manifest URL to re-run notebook 07 from Bronze, or let the notebook read the committed Silver table. Run the notebooks in order from `notebooks/`:

1. `01_bronze_manifest` records hashes and source URLs.
2. `02_silver_tables` parses each file into typed Parquet and checks it against itself.
3. `03_reconciliation_gate` rebuilds the published annual figures and writes the residuals. It stops if the declared definition does not reconcile.
4. `04_coverage_gap` measures the gap, identifies the omitted providers and draws the chart.
5. `05_dna_rebuild` rebuilds the outpatient DNA claims.
6. `06_provisional_vs_final` compares first-published monthly files (from the Internet Archive) with the final ones, and with CQI.
7. `07_deprivation_ratio` rebuilds the release's 1.85x deprivation ratio from the ECDS National Report Tables.

Shared parsers are in `src/common.py`; `src/build_notebooks.py` regenerates the notebooks.

## Limits

- First-published files could be retrieved from the Internet Archive for six months only (`06_provisional_vs_final`). July to September 2025 and March 2026 originals were not captured, the January 2026 download failed, and February was never revised. Six months is enough to show CQI follows revisions, not to say it always does.
- The report tables say planned attendances are excluded, yet the figures only reconcile with booked attendances in. "Booked" may not mean "planned"; I have not asked NHS England.
- The DNA rate's denominator includes cancellations. The rate falls under every denominator I tried, but that is not proof people attend more reliably.
