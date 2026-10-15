"""Extract the TidyTuesday summit CSVs into the DuckDB ``raw`` schema.

Kept intentionally dumb: every column lands as ``VARCHAR`` so that all typing
and sentinel handling lives in dbt as explicit, testable logic rather than
implicit I/O. This is the "EL" half of ELT; dbt is the "T".
"""

from pathlib import Path

import duckdb

BASE_URL = (
    "https://raw.githubusercontent.com/rfordatascience/tidytuesday/"
    "refs/heads/main/data/2020/2020-09-22"
)
TABLES = ("peaks", "expeditions", "members")
DB_PATH = Path(__file__).resolve().parent.parent / "warehouse.duckdb"


def main() -> None:
    con = duckdb.connect(str(DB_PATH))
    con.execute("create schema if not exists raw")
    for table in TABLES:
        con.execute(
            f"create or replace table raw.{table} as "
            f"select * from read_csv_auto('{BASE_URL}/{table}.csv', all_varchar = true)"
        )
        count = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
        print(f"raw.{table}: {count} rows")
    con.close()


if __name__ == "__main__":
    main()
