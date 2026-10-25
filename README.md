# Project A: Himalayan Expeditions Warehouse & EDA

A local-first data warehouse and exploratory analysis of the [TidyTuesday Himalayan mountaineering dataset](https://github.com/rfordatascience/tidytuesday/tree/main/data/2020/2020-09-22). Built to demonstrate a clean ELT pattern with **dbt + DuckDB** and an interactive **Marimo** notebook for analysis.

## Overview

This project transforms historical Himalayan peak and expedition data into a normalized star schema, handling real-world data quality issues (multi-valued attributes, ID collisions, missing links) along the way. The EDA notebook queries the warehouse directly and renders interactive charts.

## Architecture

```
Raw CSVs (pinned in-repo)
  └─> ingest.py (EL, checksum-verified)
       └─> raw.* schema in warehouse.duckdb
            └─> dbt (staging -> intermediate -> marts)
                 ├─> Star schema (dim_*/fct_*/bridges)
                 └─> Data quality tests
                      └─> Marimo EDA notebook (read-only)
```

## Key Features

- **Local-first & reproducible** — Raw CSVs and checksums are pinned in `transform/data/` with `SHA256SUMS`. The pipeline builds offline with no network dependency.
- **Star schema design** — Dimensions (`dim_peaks`, `dim_countries`), facts (`fct_expeditions`, `fct_members`), and bridges (`bridge_first_ascent`, `bridge_peak_first_ascent_country`) with surrogate keys and enforced referential integrity via dbt tests.
- **Handles messy real data**:
  - **ID collisions**: `expedition_id` is not unique (`KANG10101` appears for 1910 and 2010); surrogate keys (`expedition_sk`, `member_sk`) disambiguate records.
  - **Multi-valued attributes**: `first_ascent_country` (comma-separated, 156 peaks with 2+ countries) is normalized via a dbt seed (`country_aliases`) and exploded into `bridge_peak_first_ascent_country`. Historical labels (`W Germany`, `Yugoslavia`, `Russia`) are preserved.
  - **Typos & variants**: Normalized with `country_aliases.csv` (`Inida` → `India`, `Netherands` → `Netherlands`, `Swiss` → `Switzerland`, `US` → `USA`).
  - **Data cleaning**: `"NA"` → `NULL`, `SPHU` → `SPHN`, booleans cast appropriately, dates/integers typed consistently.
- **Data quality guards** — Singular dbt tests enforce invariants (e.g., both `KANG10101` expeditions preserved, complete country bridge coverage, no alias leaks).
- **Interactive analysis** — Read-only Marimo notebook (`notebooks/eda.py`) queries DuckDB directly with Altair visualizations.

## Tech Stack

- **[Python 3.12](https://www.python.org/)** with [uv](https://docs.astral.sh/uv/) for dependency management
- **[DuckDB](https://duckdb.org/)** — Embedded analytical database
- **[dbt Core](https://docs.getdbt.com/docs/core) + [dbt-duckdb](https://github.com/duckdb/dbt-duckdb)** — ELT transformations and testing
- **[Marimo](https://marimo.io/)** — Reactive Python notebook
- **[Pandas](https://pandas.pydata.org/) + [Altair](https://altair-viz.github.io/)** — Data manipulation and visualization

## Quick Start

### Prerequisites

- Python 3.12
- [uv](https://docs.astral.sh/uv/) installed

### Setup & Build

```bash
# Install dependencies
uv sync

# Load raw CSVs into warehouse.duckdb (local-first, checksum-verified)
uv run python transform/ingest.py

# Install dbt packages
cd transform && uv run dbt deps --profiles-dir .

# Build the warehouse (seeds + staging + intermediate + marts + tests)
cd transform && uv run dbt build --profiles-dir .
```

> **Note:** Always run dbt commands from inside `transform/` (DuckDB resolves paths relative to CWD). See `AGENTS.md` for details.

### Explore the Data

```bash
# Launch interactive Marimo notebook
uv run marimo edit notebooks/eda.py

# Headless smoke test
uv run marimo export html notebooks/eda.py -o /tmp/eda.html
```

## Project Structure

```
.
├── AGENTS.md              # Detailed project conventions and gotchas
├── pyproject.toml         # Single Python environment (dbt, marimo, duckdb, etc.)
├── uv.lock
├── warehouse.duckdb       # Built warehouse (gitignored)
├── notebooks/
│   └── eda.py             # Marimo EDA notebook (queries warehouse)
└── transform/
    ├── data/              # Pinned raw CSVs + SHA256SUMS (committed)
    ├── dbt_project.yml
    ├── ingest.py         # EL script
    ├── macros/           # dbt cleaning macros
    ├── models/
    │   ├── staging/      # Type casting & cleaning (views)
    │   ├── intermediate/ # Complex logic (views)
    │   └── marts/        # Star schema (tables)
    ├── profiles.yml      # dbt-duckdb config
    ├── seeds/           # Reference data (e.g., country_aliases.csv)
    └── tests/           # Singular data quality tests
```

## Data Model Highlights

| Table | Type | Description |
| --- | --- | --- |
| `dim_peaks` | Dimension | One row per peak (468 peaks) |
| `dim_countries` | Dimension | Canonical countries credited with first ascents |
| `fct_expeditions` | Fact | Expedition attempts with outcomes and conditions |
| `fct_members` | Fact | Individual climbers on expeditions |
| `bridge_first_ascent` | Bridge | Optional N:1 link from peaks to first-ascent expeditions (handles cases where one expedition first ascended multiple peaks) |
| `bridge_peak_first_ascent_country` | Bridge | Exploded first-ascent country credits (fan-out semantics — use `COUNT(DISTINCT peak_id)` when mixing grains) |

## Notes on Data Quirks

- **Country aggregation**: A peak credited to multiple countries contributes to each, so sums across countries exceed total first ascents. Always use `COUNT(DISTINCT peak_id)` if you need peak-level counts.
- **Missing links**: 3 peaks have documented first ascents/countries but no matching expedition record in the logs (`KHAM`, `LSAM`, `NILE`). These are retained in the country bridge but not in `bridge_first_ascent`.
- **KANG10101 collision**: Only `KANG10101` has duplicate business keys (1910 exploratory vs 2010 successful); all other IDs are unique.

## License & Attribution

Data sourced from [TidyTuesday](https://github.com/rfordatascience/tidytuesday) (Himalayan climbing expeditions, 2020-09-22). This project is for educational/portfolio purposes.
