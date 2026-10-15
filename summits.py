import marimo

__generated_with = "0.25.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    import duckdb

    # Load peaks data straight from GitHub into an in-memory DuckDB table
    url = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/refs/heads/main/data/2020/2020-09-22/peaks.csv"
    peaks_df = duckdb.query(f"SELECT * FROM '{url}'").df()

    # Load peaks data straight from GitHub into an in-memory DuckDB table
    url = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/refs/heads/main/data/2020/2020-09-22/members.csv"
    members_df = duckdb.query(f"SELECT * FROM '{url}'").df()

    url = "https://raw.githubusercontent.com/rfordatascience/tidytuesday/refs/heads/main/data/2020/2020-09-22/expeditions.csv"
    expeditions_df = duckdb.query(f"SELECT * FROM '{url}'").df()
    return duckdb, expeditions_df, members_df, mo, peaks_df


@app.cell
def _(peaks_df):
    peaks_df
    return


@app.cell
def _(members_df):
    members_df
    return


@app.cell
def _(expeditions_df):
    expeditions_df
    return


@app.cell
def _(mo):
    mo.md("""
    ## Clean, normalize & assign keys

    Raw CSVs use the string `"NA"` as a missing-value sentinel (even in
    numeric columns) and carry denormalized peak columns. Here we convert
    `"NA"` to real `NULL`, cast types, drop denormalized columns, and remap
    the `SPHU` typo to `SPHN`.

    `expedition_id` is **not unique**: `KANG10101` collides because the id
    encodes only a 2-digit year (1910 vs 2010). Rather than discard those
    rows, we assign **surrogate keys** (`expedition_sk`, `member_sk`) and keep
    the source ids as non-unique *business keys* — the standard warehouse
    pattern for a broken source key. `members.year` is used transiently to
    resolve which colliding expedition a member belongs to.

    `peaks.first_ascent_expedition_id` becomes a many-to-many `first_ascent`
    link table, so one expedition can be the first ascent of several peaks.
    """)
    return


@app.cell
def _(expeditions_df, members_df, peaks_df):
    import pandas as pd


    def _nullify(df):
        return df.replace({"NA": pd.NA})


    # --- peaks ----------------------------------------------------------------
    peaks_clean = _nullify(peaks_df)
    peaks_clean["height_metres"] = peaks_clean["height_metres"].astype("Int64")
    peaks_clean["first_ascent_year"] = pd.to_numeric(
        peaks_clean["first_ascent_year"], errors="coerce"
    ).astype("Int64")

    # --- expeditions ----------------------------------------------------------
    expeditions_clean = _nullify(expeditions_df)
    expeditions_clean["peak_id"] = expeditions_clean["peak_id"].replace({"SPHU": "SPHN"})
    for _col in ["basecamp_date", "highpoint_date", "termination_date"]:
        expeditions_clean[_col] = pd.to_datetime(expeditions_clean[_col], errors="coerce")
    expeditions_clean["highpoint_metres"] = pd.to_numeric(
        expeditions_clean["highpoint_metres"], errors="coerce"
    ).astype("Int64")
    expeditions_clean = expeditions_clean.drop(columns=["peak_name"])
    # Surrogate key. Sorted first so the key assignment is stable across runs;
    # expedition_id remains a non-unique business key.
    expeditions_clean = expeditions_clean.sort_values(
        ["peak_id", "year", "season", "expedition_id"]
    ).reset_index(drop=True)
    expeditions_clean.insert(
        0, "expedition_sk", pd.Series(range(1, len(expeditions_clean) + 1), dtype="Int64")
    )

    # --- members --------------------------------------------------------------
    members_clean = _nullify(members_df)
    for _col in ["age", "highpoint_metres", "death_height_metres", "injury_height_metres"]:
        members_clean[_col] = pd.to_numeric(
            members_clean[_col], errors="coerce"
        ).astype("Int64")
    # members.year is dropped below, but is needed here to disambiguate members
    # of the two colliding KANG10101 expeditions.
    members_clean = members_clean.merge(
        expeditions_clean[["expedition_id", "year", "expedition_sk"]],
        on=["expedition_id", "year"],
        how="left",
        validate="many_to_one",
    )
    members_clean = members_clean.sort_values(
        ["expedition_sk", "member_id"]
    ).reset_index(drop=True)
    members_clean.insert(
        0, "member_sk", pd.Series(range(1, len(members_clean) + 1), dtype="Int64")
    )
    members_clean = members_clean.drop(
        columns=["peak_id", "peak_name", "year", "season", "expedition_id"]
    )
    members_clean = members_clean[
        ["member_sk", "member_id", "expedition_sk"]
        + [c for c in members_clean.columns if c not in ("member_sk", "member_id", "expedition_sk")]
    ]

    # --- first_ascent (peak <-> expedition, many-to-many) ---------------------
    first_ascent_links = (
        peaks_clean[["peak_id", "first_ascent_expedition_id"]]
        .dropna(subset=["first_ascent_expedition_id"])
        .merge(
            expeditions_clean[["expedition_id", "expedition_sk"]],
            left_on="first_ascent_expedition_id",
            right_on="expedition_id",
            how="left",
        )[["peak_id", "expedition_sk"]]
        .sort_values(["peak_id", "expedition_sk"])
        .reset_index(drop=True)
    )
    peaks_clean = peaks_clean.drop(columns=["first_ascent_expedition_id"])

    peaks_clean, expeditions_clean, members_clean, first_ascent_links
    return (
        expeditions_clean,
        first_ascent_links,
        members_clean,
        pd,
        peaks_clean,
    )


@app.cell
def _(mo):
    mo.md("""
    ## Build the relational database

    Persisted to `summits.duckdb`. Surrogate primary keys (`expedition_sk`,
    `member_sk`) insulate the schema from the duplicated source ids. The
    `first_ascent` link table replaces the old soft reference, so every
    foreign key — including the formerly circular first-ascent reference — is
    now **enforced**.
    """)
    return


@app.cell
def _(
    duckdb,
    expeditions_clean,
    first_ascent_links,
    members_clean,
    peaks_clean,
):
    db_path = "summits.duckdb"
    con = duckdb.connect(db_path)

    for _table in [
        "first_ascent",
        "members",
        "members_quarantined",
        "expeditions_quarantined",
        "expeditions",
        "peaks",
    ]:
        con.execute(f"DROP TABLE IF EXISTS {_table}")

    con.execute(
        """
        CREATE TABLE peaks (
            peak_id VARCHAR PRIMARY KEY,
            peak_name VARCHAR,
            peak_alternative_name VARCHAR,
            height_metres INTEGER,
            climbing_status VARCHAR,
            first_ascent_year INTEGER,
            first_ascent_country VARCHAR
        )
        """
    )
    con.execute(
        """
        CREATE TABLE expeditions (
            expedition_sk INTEGER PRIMARY KEY,
            expedition_id VARCHAR NOT NULL,
            peak_id VARCHAR NOT NULL REFERENCES peaks (peak_id),
            year INTEGER,
            season VARCHAR,
            basecamp_date DATE,
            highpoint_date DATE,
            termination_date DATE,
            termination_reason VARCHAR,
            highpoint_metres INTEGER,
            members INTEGER,
            member_deaths INTEGER,
            hired_staff INTEGER,
            hired_staff_deaths INTEGER,
            oxygen_used BOOLEAN,
            trekking_agency VARCHAR,
            UNIQUE (expedition_id, year)
        )
        """
    )
    con.execute(
        """
        CREATE TABLE members (
            member_sk INTEGER PRIMARY KEY,
            member_id VARCHAR NOT NULL,
            expedition_sk INTEGER NOT NULL REFERENCES expeditions (expedition_sk),
            sex VARCHAR,
            age INTEGER,
            citizenship VARCHAR,
            expedition_role VARCHAR,
            hired BOOLEAN,
            highpoint_metres INTEGER,
            success BOOLEAN,
            solo BOOLEAN,
            oxygen_used BOOLEAN,
            died BOOLEAN,
            death_cause VARCHAR,
            death_height_metres INTEGER,
            injured BOOLEAN,
            injury_type VARCHAR,
            injury_height_metres INTEGER
        )
        """
    )
    con.execute(
        """
        CREATE TABLE first_ascent (
            peak_id VARCHAR NOT NULL REFERENCES peaks (peak_id),
            expedition_sk INTEGER NOT NULL REFERENCES expeditions (expedition_sk),
            PRIMARY KEY (peak_id, expedition_sk)
        )
        """
    )

    for _name, _frame in [
        ("peaks", peaks_clean),
        ("expeditions", expeditions_clean),
        ("members", members_clean),
        ("first_ascent", first_ascent_links),
    ]:
        _cols = ", ".join(_frame.columns)
        con.register("_src", _frame)
        con.execute(f"INSERT INTO {_name} ({_cols}) SELECT {_cols} FROM _src")
        con.unregister("_src")

    db_path
    return (con,)


@app.cell
def _(mo):
    mo.md("""
    ## Verify integrity

    Row counts, enforced-FK checks, the retained `KANG10101` records, and the
    cross-peak first-ascent links (now modelled explicitly).
    """)
    return


@app.cell
def _(con, pd):
    def _scalar(sql):
        return con.execute(sql).fetchone()[0]


    integrity_report = pd.DataFrame(
        [
            ("peaks rows", _scalar("SELECT count(*) FROM peaks")),
            ("expeditions rows", _scalar("SELECT count(*) FROM expeditions")),
            ("members rows", _scalar("SELECT count(*) FROM members")),
            ("first_ascent rows", _scalar("SELECT count(*) FROM first_ascent")),
            (
                "FK orphans: expeditions.peak_id",
                _scalar(
                    "SELECT count(*) FROM expeditions e "
                    "LEFT JOIN peaks p USING (peak_id) WHERE p.peak_id IS NULL"
                ),
            ),
            (
                "FK orphans: members.expedition_sk",
                _scalar(
                    "SELECT count(*) FROM members m "
                    "LEFT JOIN expeditions e USING (expedition_sk) "
                    "WHERE e.expedition_sk IS NULL"
                ),
            ),
            (
                "FK orphans: first_ascent",
                _scalar(
                    "SELECT count(*) FROM first_ascent fa "
                    "LEFT JOIN peaks p USING (peak_id) "
                    "LEFT JOIN expeditions e USING (expedition_sk) "
                    "WHERE p.peak_id IS NULL OR e.expedition_sk IS NULL"
                ),
            ),
            (
                "duplicate expedition_id keys (expected 1: KANG10101)",
                _scalar(
                    "SELECT count(*) FROM ("
                    "SELECT expedition_id FROM expeditions "
                    "GROUP BY expedition_id HAVING count(*) > 1)"
                ),
            ),
            (
                "KANG10101 expeditions preserved",
                _scalar(
                    "SELECT count(*) FROM expeditions WHERE expedition_id = 'KANG10101'"
                ),
            ),
            (
                "KANG10101 members preserved",
                _scalar(
                    "SELECT count(*) FROM members m JOIN expeditions e "
                    "USING (expedition_sk) WHERE e.expedition_id = 'KANG10101'"
                ),
            ),
        ],
        columns=["check", "value"],
    ).set_index("check")

    integrity_report
    return


@app.cell
def _(con):
    cross_peak_ascents = con.execute(
        """
        SELECT
            p.peak_id,
            p.peak_name,
            p.first_ascent_year,
            e.expedition_id,
            main.peak_id   AS main_peak_id,
            main.peak_name AS main_peak_name
        FROM first_ascent fa
        JOIN peaks p ON p.peak_id = fa.peak_id
        JOIN expeditions e ON e.expedition_sk = fa.expedition_sk
        JOIN peaks main ON main.peak_id = e.peak_id
        WHERE e.peak_id <> fa.peak_id
        ORDER BY p.peak_id
        """
    ).df()

    cross_peak_ascents
    return


if __name__ == "__main__":
    app.run()
