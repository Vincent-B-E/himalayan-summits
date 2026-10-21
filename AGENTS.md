# AGENTS.md

## What this is

A warehouse + EDA project on the TidyTuesday Himalayan / mountaineering dataset
(2020-09-22). Two halves:

- `transform/` — a dbt + DuckDB pipeline that ELs raw CSVs and builds a star
  schema (dimension + facts + a many-to-many bridge) in `warehouse.duckdb`.
- `notebooks/eda.py` — a read-only marimo notebook that queries that warehouse
  and renders Altair charts. It consumes the marts; it does not transform data.

One consolidated Python env at the repo root serves both halves (dbt + marimo +
duckdb + pandas + altair). There is no second `.venv` under `transform/`.

## Commands

```bash
# One-time / after changing deps (repo root)
uv sync

# Build the warehouse
uv run python transform/ingest.py                              # raw CSVs -> raw.* (local-first)
cd transform && uv run dbt deps --profiles-dir .              # install dbt_utils
cd transform && uv run dbt build --profiles-dir .             # staging + marts + tests

# EDA notebook
uv run marimo edit notebooks/eda.py                            # interactive
uv run marimo export html notebooks/eda.py -o /tmp/eda.html    # headless smoke test
```

**Run dbt from inside `transform/`** (the `cd transform` above is required, not
optional — see the profiles.yml gotcha below). `uv run` from a subdirectory still
resolves the root `.venv`, so no second env is needed.

The dbt project ships data tests; the notebook's smoke test is the headless
`marimo export` above (it executes every cell and exits non-zero if any cell
raises). Do not invent other verification steps.

## Data resilience

The three source CSVs are **pinned in-repo** at `transform/data/` (peaks,
expeditions, members) with a `SHA256SUMS` manifest. `ingest.py` is local-first:
it reads those committed files and only reaches for the network if a file is
missing. Checksums make upstream drift loud instead of silent — if TidyTuesday
ever rewrites this historical extract, ingest fails with an actionable message
rather than quietly building a different warehouse. The whole point is that the
project builds **offline** and is immune to URL rot.

## Warehouse

`warehouse.duckdb` at the repo root (gitignored; rebuilt by ingest + dbt). Star
schema:

- `dim_peaks` (PK `peak_id`) — the dimension.
- `fct_expeditions` (PK `expedition_sk`, business key `expedition_id`, FK
  `peak_id`, unique `(expedition_id, year)`) — fact.
- `fct_members` (PK `member_sk`, business key `member_id`, FK `expedition_sk`)
  — fact.
- `bridge_first_ascent` (PK `(peak_id, expedition_sk)`, FKs to both) — the
  many-to-many link letting one expedition be the first ascent of several peaks.

`expedition_id` is **not unique** in the source: `KANG10101` collides because
the id encodes only a 2-digit year (1910 vs 2010). Surrogate keys retain every
record while leaving the source ids as non-unique business keys; `members.year`
is used transiently to disambiguate the colliding members at load time.

- `"NA"` string sentinels in the CSVs become real `NULL`; denormalized peak
  columns are dropped; `*year*`/`age`/`*_metres` cast to `INTEGER`, `*_date` to
  `DATE`.
- The `SPHU` typo is remapped to `SPHN`.
- Booleans arrive as the strings `'TRUE'`/`'FALSE'`; the notebook casts them to
  0/1 via a `as_flag(col)` helper before charting.

## dbt pipeline (transform/)

dbt Core + the `dbt-duckdb` adapter; DuckDB is the warehouse (no server). Flow:
`ingest.py` ELs the three CSVs verbatim (all columns `VARCHAR`) into a `raw`
schema; dbt then does the T in SQL.

Layout:

- `data/` — pinned raw CSVs + `SHA256SUMS` (committed; the offline failsafe).
- `ingest.py` — load `raw.{peaks,expeditions,members}` (idempotent,
  local-first, checksum-verified).
- `macros/cleaning.sql` — `to_null` / `as_int` / `as_date` macros.
- `models/staging/` (views) — `stg_peaks`, `stg_expeditions`, `stg_members`.
- `models/marts/` (tables) — `dim_peaks`, `fct_expeditions`, `fct_members`,
  `bridge_first_ascent`.
- `tests/` — singular tests guarding the data quirks (e.g.
  `assert_kang10101_preserved`).

`profiles.yml` is committed and points at `../warehouse.duckdb` (overridable via
the `DBT_DUCKDB_PATH` env var).

**profiles.yml gotcha:** DuckDB resolves that `path` relative to the directory
you launch dbt from — NOT relative to `profiles.yml`. Running `dbt build` from
the repo root makes `../warehouse.duckdb` resolve *outside* the repo and silently
creates a stray empty DB. That is why every dbt command above runs from inside
`transform/`.

dbt **cannot emit PK/FK constraints** (and DuckDB cannot `ALTER TABLE ADD
FOREIGN KEY`), so referential integrity is asserted with tests instead:
`unique`/`not_null`, `dbt_utils.unique_combination_of_columns` (composite keys),
`relationships` (FKs), and the KANG10101 preservation test.

## Editing the notebook (notebooks/eda.py)

- **Each cell that uses `mo` must declare it as a parameter AND some cell must
  export `mo`** (`import marimo as mo` in a dedicated cell that `return`s it).
  marimo only injects `mo` into consumers if at least one cell exports it —
  without that export cell, every `mo.*` call raises `NameError` at runtime.
  This is the single most common way to break the notebook.
- Names starting with `_` are **cell-local** in marimo and cannot cross cells,
  even if listed in a `return`. Use a plain name (`hired_filter`, not
  `_hired_filter`) for anything another cell consumes.
- Respect the dependency graph: a variable is threaded via the producing cell's
  `return` and the consuming cell's signature (`def _(con, mo):`). Adding or
  renaming a variable means updating the producer's return and every consumer's
  params.
- SQL analysis runs **in DuckDB** via `mo.sql(query, engine=con, output=False)`;
  only small aggregates reach the browser where Altair renders them. Keep heavy
  aggregation in SQL, not pandas.
- Prefer `uv run marimo edit notebooks/eda.py` over hand-editing. marimo rewrites
  the file on save and owns the `__generated_with` header.
- Smoke-test edits with the headless export command above before assuming they
  work — it catches the `mo`-injection and cell-local-name errors that a plain
  `python` run will not.

## Housekeeping

- Commit `uv.lock` and `.python-version` (reproducibility, Python 3.12).
- Commit `transform/data/` (the pinned raw CSVs + `SHA256SUMS`) — this is the
  offline failsafe, not a build artifact.
- Commit `transform/package-lock.yml` (pins installed dbt package versions).
- Never commit `__marimo__/`, `marimo/_static/`, or `marimo/_lsp/`.
- Never commit `warehouse.duckdb` or any `*.duckdb` / `*.duckdb.wal` — build
  artifacts, already in `.gitignore`.
- Never commit dbt artifacts: `transform/dbt_packages/`, `transform/logs/`,
  `transform/target/`, `transform/.user.yml` — all in `.gitignore`.
- `transform/` is **not** a separate uv project — no `transform/.venv` or
  `transform/uv.lock`. The root env is the single source of dependency truth.

## WSL note

This project lives on native ext4 (`~/projects/Project_A`), not under `/mnt/c`.
Always invoke tooling via `uv run` from the project root; Windows Python on the
WSL `PATH` (`/mnt/c/.../Python312/`) can shadow `python`/`marimo`/`uv` and
silently create Windows venvs.
