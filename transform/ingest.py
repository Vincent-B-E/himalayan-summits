"""Extract the TidyTuesday summit CSVs into the DuckDB ``raw`` schema.

Kept intentionally dumb: every column lands as ``VARCHAR`` so that all typing
and sentinel handling lives in dbt as explicit, testable logic rather than
implicit I/O. This is the "EL" half of ELT; dbt is the "T".

Data resilience
---------------
The three source CSVs are **pinned in-repo** under ``transform/data/`` and
guarded by ``data/SHA256SUMS``. Ingest is therefore local-first and works
offline: it reads the committed files, and only reaches for the network if a
file is missing (first-ever bootstrap, or a deliberately re-fetched copy).

Checksums make upstream drift loud instead of silent — if TidyTuesday ever
rewrites this historical extract, ingest fails with an actionable message
rather than quietly building a different warehouse.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.request import urlopen

import duckdb

BASE_URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "refs/heads/main/data/2020/2020-09-22"
)
TABLES = ("peaks", "expeditions", "members")

HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
SUMS_PATH = DATA_DIR / "SHA256SUMS"
DB_PATH = HERE.parent / "warehouse.duckdb"


def _read_manifest() -> dict[str, str]:
    """Parse ``sha256sum``-style manifest into {filename: digest}."""
    if not SUMS_PATH.exists():
        return {}
    manifest: dict[str, str] = {}
    for line in SUMS_PATH.read_text().splitlines():
        digest, _, name = line.partition("  ")
        if name.strip():
            manifest[name.strip()] = digest.strip()
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _download(table: str) -> Path:
    dest = DATA_DIR / f"{table}.csv"
    url = f"{BASE_URL}/{table}.csv"
    print(f"  bootstrapping {table}.csv from {url}")
    with urlopen(url) as response, dest.open("wb") as out:
        out.write(response.read())
    return dest


def _local_path(table: str) -> Path:
    """Return a verified local CSV path, downloading it only if absent."""
    path = DATA_DIR / f"{table}.csv"
    if not path.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        path = _download(table)

    expected = _read_manifest().get(path.name)
    if expected is not None:
        actual = _sha256(path)
        if actual != expected:
            raise SystemExit(
                f"checksum mismatch for {path.name}\n"
                f"  expected {expected}\n"
                f"  actual   {actual}\n"
                "The pinned raw file has changed. If this is intentional, "
                "regenerate the manifest:\n"
                "  cd transform/data && "
                "sha256sum peaks.csv expeditions.csv members.csv > SHA256SUMS"
            )
    return path


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    con.execute("create schema if not exists raw")
    for table in TABLES:
        path = _local_path(table)
        con.execute(
            f"create or replace table raw.{table} as "
            f"select * from read_csv_auto('{path}', all_varchar = true)"
        )
        count = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
        print(f"raw.{table}: {count} rows  <- data/{path.name}")
    con.close()


if __name__ == "__main__":
    main()
