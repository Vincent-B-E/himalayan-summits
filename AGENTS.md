# AGENTS.md

## What this is

A marimo notebook for exploratory data analysis (EDA) on the TidyTuesday
mountaineering / Himalayan dataset. `summits.py` is the entire application: a
series of `@app.cell` functions plus a `app.run()` guard. There is no package
structure, CLI, or server code.

## Commands

```bash
uv sync                        # create/refresh the native Linux .venv from uv.lock
uv run marimo edit summits.py  # open the notebook for interactive editing
uv run marimo run summits.py   # serve the notebook read-only
```

There are **no tests, lint, typecheck, or CI** in this repo. Do not invent
verification steps; the closest thing to a smoke test is opening the notebook.

## Runtime quirk

Cells fetch CSVs at execution time from `raw.githubusercontent.com` via DuckDB
URL queries (`peaks.csv`, `members.csv`, `expeditions.csv`, TidyTuesday
2020-09-22). **Network access is required** and there is no local data or test
fixtures. A cell will fail offline.

## Editing

- Respect marimo's dependency graph: variables are threaded through each cell's
  return tuple, and cell function signatures declare their inputs (e.g.
  `def _(peaks_df):`). Adding/renaming a variable means updating the return of
  the producing cell and the parameters of every consumer.
- Prefer `uv run marimo edit summits.py` over hand-editing. marimo rewrites the
  file on save and owns the `__generated_with` header.
- The header pins `__generated_with = "0.24.2"` while `uv.lock` resolves
  marimo 0.25.1, so that version string may bump the first time the notebook is
  opened/saved.

## Housekeeping

- Commit `uv.lock` (reproducibility).
- Never commit `__marimo__/`, `marimo/_static/`, or `marimo/_lsp/` — already in
  `.gitignore`.

## WSL note

This project lives on native ext4 (`~/projects/Project_A`), not under `/mnt/c`.
Always invoke tooling via `uv run` from the project root; Windows Python on the
WSL `PATH` (`/mnt/c/.../Python312/`) can shadow `python`/`marimo`/`uv` and
silently create Windows venvs.
