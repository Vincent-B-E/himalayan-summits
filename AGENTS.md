# AGENTS.md

## What this is

A marimo notebook for exploratory data analysis (EDA) on the TidyTuesday
mountaineering / Himalayan dataset. `summits.py` is the notebook: a series of
`@app.cell` functions plus an `app.run()` guard. The canonical, productionized
pipeline built from the same data lives in `transform/` (a dbt + DuckDB project).

## Commands

```bash
# Notebook (repo root)
uv sync                        # create/refresh the native Linux .venv from uv.lock
uv run marimo edit summits.py  # open the notebook for interactive editing
uv run marimo run summits.py   # serve the notebook read-only

# dbt pipeline (transform/, independent uv project w/ its own .venv + uv.lock)
cd transform
uv sync                                  # create/refresh transform/.venv
./.venv/bin/python ingest.py             # load raw CSVs -> raw.* in ../warehouse.duckdb
./.venv/bin/dbt deps --profiles-dir .    # install dbt_utils (once / on packages.yml change)
./.venv/bin/dbt build --profiles-dir .   # build models + run data tests
./.venv/bin/dbt debug --profiles-dir .   # connection troubleshooting
```

There are **no tests, lint, typecheck, or CI** for the notebook; the closest
thing to a smoke test is opening it. The dbt project is the exception — it ships
dbt data tests (see the dbt section). Do not invent other verification steps.

## Runtime quirk

Cells fetch CSVs at execution time from `raw.githubusercontent.com` via DuckDB
URL queries (`peaks.csv`, `members.csv`, `expeditions.csv`, TidyTuesday
2020-09-22). **Network access is required** and there is no local data or test
fixtures. A cell will fail offline.

## Relational database

Downstream cells clean the raw CSVs and build a persisted `summits.duckdb`
(gitignored, regenerated on every run). Schema:

- `peaks` (PK `peak_id`)
- `expeditions` (PK surrogate `expedition_sk`, business key `expedition_id`,
  FK `peak_id`, unique `(expedition_id, year)`)
- `members` (PK surrogate `member_sk`, business key `member_id`, FK
  `expedition_sk`)
- `first_ascent` (M:N link, PK `(peak_id, expedition_sk)`, FKs to both tables)

`expedition_id` is **not unique** in the source: `KANG10101` collides because
the id encodes only a 2-digit year (1910 vs 2010). Surrogate keys retain every
record while leaving the source ids as non-unique business keys; `members.year`
is used transiently to disambiguate the colliding members at load time. The
former single `peaks.first_ascent_expedition_id` column is modelled as the
`first_ascent` many-to-many table, so the formerly circular reference is now an
**enforced** foreign key (not a soft FK).

- `"NA"` string sentinels in the CSVs are converted to real `NULL`; denormalized
  peak columns are dropped; `*year*`/`age`/`*_metres` are cast to `INTEGER` and
  `*_date` to `DATE`.
- The `SPHU` typo is remapped to `SPHN`.

## dbt pipeline (transform/)

`transform/` is a **standalone** uv project (its own `.venv` and `uv.lock`; it is
*not* a workspace member of the root). It reimplements the notebook's
clean-and-load as a dbt project — dbt Core + the `dbt-duckdb` adapter, with
DuckDB as the warehouse (no server).

Flow: `ingest.py` ELs the three raw CSVs verbatim (all columns `VARCHAR`) into a
`raw` schema in the repo-root `warehouse.duckdb`; dbt then does the T in SQL.

Layout:

- `ingest.py` — load `raw.{peaks,expeditions,members}` (idempotent).
- `macros/cleaning.sql` — `to_null` / `as_int` / `as_date` macros.
- `models/staging/` (views) — `stg_peaks`, `stg_expeditions`, `stg_members`:
  typed, `"NA"`->`NULL`, `SPHU`->`SPHN`, surrogate keys added.
- `models/marts/` (tables) — `dim_peaks`, `fct_expeditions`, `fct_members`,
  `bridge_first_ascent`.
- `tests/` — singular tests guarding the data quirks.

`profiles.yml` is committed here and points at `../warehouse.duckdb`
(overridable via the `DBT_DUCKDB_PATH` env var); run dbt with `--profiles-dir .`
from inside `transform/`.

dbt **cannot emit PK/FK constraints** (and DuckDB cannot `ALTER TABLE ADD
FOREIGN KEY`), so referential integrity is asserted with tests instead:
`unique`/`not_null`, `dbt_utils.unique_combination_of_columns` (composite keys),
`relationships` (FKs), and `assert_kang10101_preserved` (the 1910/2010 collision
must keep both rows). The same `NA`/surrogate-key/`first_ascent` decisions as
the notebook apply.

## Editing

- Respect marimo's dependency graph: variables are threaded through each cell's
  return tuple, and cell function signatures declare their inputs (e.g.
  `def _(peaks_df):`). Adding/renaming a variable means updating the return of
  the producing cell and the parameters of every consumer.
- Prefer `uv run marimo edit summits.py` over hand-editing. marimo rewrites the
  file on save and owns the `__generated_with` header.
- The header tracks the marimo version that last saved the file (currently
  `0.25.1`, matching `uv.lock`).

## Environment / sandbox gotcha

Run against the project `.venv` using the `uv run marimo` commands above. If
marimo is launched in **sandbox mode** (`--sandbox`; the VS Code marimo
extension defaults to this), the kernel ignores `.venv` and `pyproject.toml`
and instead builds a throwaway uv environment from the notebook's PEP 723
`# /// script` header. `import duckdb` then fails even after a correct
`uv sync`, because the project venv is never used. Keep sandbox off so
`pyproject.toml` remains the single source of dependency truth.

## Housekeeping

- Commit `uv.lock` (root) and `transform/uv.lock` (reproducibility). The two
  projects are independent; do **not** merge them into a uv workspace.
- Commit `transform/package-lock.yml` (pins the installed dbt package versions).
- Never commit `__marimo__/`, `marimo/_static/`, or `marimo/_lsp/` — already in
  `.gitignore`.
- Never commit `warehouse.duckdb` / `summits.duckdb` (and any `.duckdb.wal`) —
  build artifacts, already in `.gitignore`.
- Never commit dbt artifacts: `transform/dbt_packages/`, `transform/logs/`,
  `transform/target/`, `transform/.user.yml` — all in `.gitignore`.

## WSL note

This project lives on native ext4 (`~/projects/Project_A`), not under `/mnt/c`.
Always invoke tooling via `uv run` from the project root; Windows Python on the
WSL `PATH` (`/mnt/c/.../Python312/`) can shadow `python`/`marimo`/`uv` and
silently create Windows venvs.
