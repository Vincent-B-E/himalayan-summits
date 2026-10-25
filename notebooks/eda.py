import marimo

__generated_with = "0.25.2"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Himalayan Summits — EDA on the warehouse

    This notebook is the **consumer** side of the project. The heavy lifting
    (cleaning, typing, surrogate keys, referential integrity) already happened
    upstream in the dbt pipeline under `transform/`; here we simply query the
    finished `warehouse.duckdb`.

    **How to read it.** Every analytical table below is produced by a SQL cell
    (`mo.sql`) running *inside DuckDB*, against the marts built by dbt. The
    aggregate that leaves the warehouse is small; Altair then renders it
    declaratively in the browser. The warehouse does the crunching, Python
    stays out of the way.
    """)
    return


@app.cell
def _():
    from pathlib import Path
    import duckdb
    import altair as alt

    # Resolve the warehouse relative to this file, not the process CWD, so the
    # notebook works whether you launch marimo from the repo root or notebooks/.
    here = Path(__file__).resolve().parent
    warehouse = here.parent / "warehouse.duckdb"

    # Read-only: this notebook must never mutate what dbt built.
    con = duckdb.connect(str(warehouse), read_only=True)

    # Booleans arrived from the CSV as the strings 'TRUE'/'FALSE'; give Altair
    # real 0/1 integers so quantitative encodings (and tooltips) behave.
    def as_flag(col):
        return f"CASE WHEN {col} = 'TRUE' THEN 1 ELSE 0 END"

    return alt, as_flag, con


@app.cell
def _(mo):
    mo.md(r"""
    ## The shape of the data

    Four marts. `dim_peaks` is the dimension; the rest are facts keyed by
    surrogate keys (`*_sk`). `bridge_first_ascent` is the many-to-many link
    that lets one expedition be the first ascent of several peaks — the
    relationship the original single-column design could not express.
    """)
    return


@app.cell
def _(con, mo):
    overview = mo.sql(
        query="""
            SELECT 'peaks'           AS mart, count(*) AS rows FROM main.dim_peaks
            UNION ALL SELECT 'expeditions',   count(*) FROM main.fct_expeditions
            UNION ALL SELECT 'members',       count(*) FROM main.fct_members
            UNION ALL SELECT 'first_ascents', count(*) FROM main.bridge_first_ascent
        """,
        engine=con
    )
    overview
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 1. Peaks: climbed vs unclimbed

    Of 468 surveyed peaks, most have been climbed. The unclimbed remainder
    skews high and remote — the tallest unclimbed peaks are the ones that
    still resist a documented ascent.
    """)
    return


@app.cell
def _(alt, con, mo):
    status = mo.sql(
        query="""
            SELECT climbing_status, count(*) AS peaks
            FROM main.dim_peaks
            GROUP BY 1
            ORDER BY peaks DESC
        """,
        engine=con,
        output=False,
    )

    chart = (
        alt.Chart(status)
        .mark_bar()
        .encode(
            x=alt.X("peaks:Q", title="Number of peaks"),
            y=alt.Y("climbing_status:N", title=None, sort="-x"),
            color=alt.Color("climbing_status:N", scale=alt.Scale(scheme="set2"), legend=None),
            tooltip=[
                alt.Tooltip("climbing_status:N", title="Status"),
                alt.Tooltip("peaks:Q", title="Peaks", format=","),
            ],
        )
        .properties(height=140,title="Climbing status of all 468 peaks")
    )
    mo.vstack([chart, mo.md(f"**{int(status.peaks.sum()):,}** peaks surveyed.")])
    return


@app.cell
def _(mo):
    mo.md(r"""
    Height distribution, split by climbing status. Unclimbed peaks cluster
    toward the higher end — altitude and remoteness are exactly what make a
    peak hard to put a documented ascent on.
    """)
    return


@app.cell
def _(alt, con, mo):
    heights = mo.sql(
        query="""
            SELECT
                CASE
                    WHEN height_metres < 6000 THEN '< 6000'
                    WHEN height_metres < 7000 THEN '6000–7000'
                    WHEN height_metres < 8000 THEN '7000–8000'
                    ELSE '8000+'
                END AS band,
                climbing_status,
                count(*) AS peaks
            FROM main.dim_peaks
            WHERE height_metres IS NOT NULL
            GROUP BY 1, 2
            ORDER BY
                CASE band
                    WHEN '< 6000' THEN 1 WHEN '6000–7000' THEN 2
                    WHEN '7000–8000' THEN 3 ELSE 4 END
        """,
        engine=con,
        output=False,
    )

    height_chart = (
        alt.Chart(heights)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X("peaks:Q", title="Number of peaks"),
            y=alt.Y("band:N", title="Height band (m)", sort=["< 6000", "6000–7000", "7000–8000", "8000+"]),
            color=alt.Color("climbing_status:N", scale=alt.Scale(domain=["Climbed", "Unclimbed"], range=["#4c78a8", "#e45756"])),
            tooltip=["band:N", "climbing_status:N", alt.Tooltip("peaks:Q", format=",")],
        )
        .properties(height=220, title="Peak heights by climbing status")
    )
    height_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 2. Expedition outcomes over time

    When expeditions *do* end without success, what stops them? Weather and
    conditions dominate; illness and technical difficulty trail; accidents
    (death or serious injury) are rarer but real. This is the terminations
    breakdown across all non-success outcomes.
    """)
    return


@app.cell
def _(alt, con, mo):
    outcomes = mo.sql(
        query="""
            SELECT
                (year / 10) * 10 AS decade,
                sum(CASE WHEN termination_reason = 'Success (main peak)' THEN 1 ELSE 0 END) AS succeeded,
                count(*) AS expeditions
            FROM main.fct_expeditions
            WHERE year >= 1900
            GROUP BY 1
            ORDER BY 1
        """,
        engine=con,
        output=False,
    )
    outcomes["success_rate"] = outcomes.succeeded / outcomes.expeditions

    line = (
        alt.Chart(outcomes)
        .mark_line(point=alt.OverlayMarkDef(color="#4c78a8"), color="#4c78a8")
        .encode(
            x=alt.X("decade:O", title="Decade", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("success_rate:Q", title="Success rate", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
            tooltip=[
                alt.Tooltip("decade:O", title="Decade"),
                alt.Tooltip("success_rate:Q", title="Success rate", format=".1%"),
                alt.Tooltip("expeditions:Q", title="Expeditions", format=","),
            ],
        )
        .properties(height=260, title="Expeditions reaching their main peak, by decade")
    )
    line
    return


@app.cell
def _(mo):
    mo.md(r"""
    When expeditions *do* end without success, what stops them? Weather and
    conditions dominate; illness and technical difficulty trail; accidents
    (death or serious injury) are rarer but real. This is the terminations
    breakdown across all non-success outcomes.
    """)
    return


@app.cell
def _(alt, con, mo):
    reasons = mo.sql(
        query="""
            SELECT termination_reason AS reason, count(*) AS expeditions
            FROM main.fct_expeditions
            WHERE termination_reason IS NOT NULL
              AND termination_reason <> 'Success (main peak)'
            GROUP BY 1
            ORDER BY expeditions DESC
            LIMIT 8
        """,
        engine=con,
        output=False,
    )

    reason_chart = (
        alt.Chart(reasons)
        .mark_bar(cornerRadius=3)
        .encode(
            x=alt.X("expeditions:Q", title="Expeditions"),
            y=alt.Y("reason:N", title=None, sort="-x"),
            color=alt.Color("expeditions:Q", scale=alt.Scale(scheme="reds"), legend=None),
            tooltip=["reason:N", alt.Tooltip("expeditions:Q", format=",")],
        )
        .properties(height=240, title="Why expeditions did not reach the main peak")
    )
    reason_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 3. Oxygen usage over time

    Supplemental oxygen transforms high-altitude climbing. Its use rose
    sharply from mid-century, plateaued, then — after the commercialized
    1990s boom — began a gradual decline as climbers pursued purer styles.
    """)
    return


@app.cell
def _(alt, con, mo):
    oxygen = mo.sql(
        query="""
            SELECT
                (year / 10) * 10 AS decade,
                sum(CASE WHEN oxygen_used = 'TRUE' THEN 1 ELSE 0 END) AS with_oxygen,
                count(*) AS expeditions
            FROM main.fct_expeditions
            WHERE year >= 1900
            GROUP BY 1
            ORDER BY 1
        """,
        engine=con,
        output=False,
    )
    oxygen["pct_oxygen"] = oxygen.with_oxygen / oxygen.expeditions

    oxygen_chart = (
        alt.Chart(oxygen)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#54a24b")
        .encode(
            x=alt.X("decade:O", title="Decade", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("pct_oxygen:Q", title="Share using oxygen", axis=alt.Axis(format=".0%"), scale=alt.Scale(domain=[0, 1])),
            tooltip=[
                alt.Tooltip("decade:O", title="Decade"),
                alt.Tooltip("pct_oxygen:Q", title="Share with oxygen", format=".1%"),
                alt.Tooltip("with_oxygen:Q", title="With oxygen", format=","),
            ],
        )
        .properties(height=260, title="Expeditions using supplemental oxygen, by decade")
    )
    oxygen_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 4. Member risk & fatality

    Risk is not evenly distributed. Hired staff (guides, Sherpas, and porters)
    carry a substantially higher fatality rate than the expedition members who
    hire them — the starkest equity story in the dataset. Filtering on the
    controls below re-draws the chart from the warehouse.
    """)
    return


@app.cell
def _(mo):
    hired_filter = mo.ui.dropdown(
        options=["All staff", "Members only", "Hired staff only"],
        value="All staff",
        label="Show:",
    )
    hired_filter
    return (hired_filter,)


@app.cell
def _(alt, as_flag, con, hired_filter, mo):
    # The widget's selection becomes a WHERE clause that DuckDB evaluates, so the
    # aggregation still happens in the warehouse — never in pandas.
    staff_clause = {
        "Members only": "WHERE hired = 'FALSE'",
        "Hired staff only": "WHERE hired = 'TRUE'",
        "All staff": "",
    }[hired_filter.value]

    risk = mo.sql(
        query=f"""
            SELECT
                CASE
                    WHEN highpoint_metres IS NULL THEN 'unknown'
                    WHEN highpoint_metres < 6000 THEN '< 6000 m'
                    WHEN highpoint_metres < 7000 THEN '6000–7000 m'
                    WHEN highpoint_metres < 8000 THEN '7000–8000 m'
                    ELSE '8000+ m'
                END AS band,
                count(*) AS people,
                sum({as_flag('died')}) AS deaths,
                1.0 * sum({as_flag('died')}) / count(*) AS fatality_rate
            FROM main.fct_members
            {staff_clause}
            GROUP BY 1
            ORDER BY
                CASE band
                    WHEN '< 6000 m' THEN 1 WHEN '6000–7000 m' THEN 2
                    WHEN '7000–8000 m' THEN 3 WHEN '8000+ m' THEN 4 ELSE 5 END
        """,
        engine=con,
        output=False,
    )

    risk_chart = (
        alt.Chart(risk)
        .mark_bar(cornerRadius=3, color="#e45756")
        .encode(
            x=alt.X("band:N", title="High-point reached (m)", sort=["< 6000 m", "6000–7000 m", "7000–8000 m", "8000+ m", "unknown"]),
            y=alt.Y("fatality_rate:Q", title="Fatality rate", axis=alt.Axis(format=".1%")),
            tooltip=[
                alt.Tooltip("band:N", title="Band"),
                alt.Tooltip("people:Q", title="People", format=","),
                alt.Tooltip("deaths:Q", title="Deaths", format=","),
                alt.Tooltip("fatality_rate:Q", title="Fatality rate", format=".2%"),
            ],
        )
        .properties(height=280, title=f"Fatality rate by high-point — {hired_filter.value}")
    )
    risk_chart
    return


@app.cell
def _(alt, as_flag, con, mo):
    # Side-by-side: hired vs members, no widget — the equity gap at a glance.
    hired_vs_member = mo.sql(
        query=f"""
            SELECT
                CASE WHEN hired = 'TRUE' THEN 'Hired staff' ELSE 'Member' END AS role,
                count(*) AS people,
                sum({as_flag('died')}) AS deaths,
                1.0 * sum({as_flag('died')}) / count(*) AS fatality_rate
            FROM main.fct_members
            GROUP BY 1
            ORDER BY fatality_rate DESC
        """,
        engine=con,
        output=False,
    )

    hired_chart = (
        alt.Chart(hired_vs_member)
        .mark_bar(cornerRadius=3)
        .encode(
            x=alt.X("role:N", title=None),
            y=alt.Y("fatality_rate:Q", title="Fatality rate", axis=alt.Axis(format=".1%")),
            color=alt.Color("role:N", scale=alt.Scale(domain=["Hired staff", "Member"], range=["#e45756", "#4c78a8"]), legend=None),
            tooltip=["role:N", alt.Tooltip("people:Q", format=","), alt.Tooltip("deaths:Q", format=","), alt.Tooltip("fatality_rate:Q", format=".2%")],
        )
        .properties(height=240, title="Fatality rate: hired staff vs members")
    )
    hired_chart
    return


@app.cell
def _(mo):
    mo.md(r"""
    Fatality risk climbs steeply with altitude. Above 8,000 m — the "death
    zone" — the rate is roughly an order of magnitude higher than below 6,000 m,
    and that is before separating hired staff from members.
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## 5. First-ascent history

    The `bridge_first_ascent` table links each peak to the expedition that first
    stood on it. Because it is a proper many-to-many bridge, an expedition that
    first ascended *several* peaks appears once per peak — so the bridge has
    333 rows but only 332 distinct expeditions. The single surplus row is the
    1962 Sharphu expedition (`SPH462101`), which is credited with two summits
    (Sharphu IV and Nupchu). A single-column design could not have expressed
    this without duplicating or dropping a record.
    """)
    return


@app.cell
def _(alt, con, mo):
    first_ascents = mo.sql(
        query="""
            SELECT p.first_ascent_year AS year, p.first_ascent_country AS country
            FROM main.bridge_first_ascent b
            JOIN main.dim_peaks p ON p.peak_id = b.peak_id
            WHERE p.first_ascent_year >= 1900
        """,
        engine=con,
        output=False,
    )

    fa_by_decade = (
        first_ascents.assign(decade=(first_ascents.year // 10 * 10).astype(int))
        .groupby("decade")
        .size()
        .reset_index(name="first_ascents")
    )

    fa_chart = (
        alt.Chart(fa_by_decade)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#b279a2")
        .encode(
            x=alt.X("decade:O", title="Decade", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("first_ascents:Q", title="First ascents recorded"),
            tooltip=[alt.Tooltip("decade:O", title="Decade"), alt.Tooltip("first_ascents:Q", format=",")],
        )
        .properties(height=250, title="Documented first ascents, by decade")
    )
    fa_chart
    return (first_ascents,)


@app.cell
def _(mo):
    mo.md(r"""
    Which nations are credited with first ascents? The counts reflect who has
    historically been credited in the record — an editorial and political
    artifact of the source data as much as a sporting one.
    """)
    return


@app.cell
def _(alt, first_ascents):
    top_countries = (
        first_ascents[first_ascents.country.notna()]
        .groupby("country")
        .size()
        .reset_index(name="first_ascents")
        .sort_values("first_ascents", ascending=False)
        .head(10)
    )

    country_chart = (
        alt.Chart(top_countries)
        .mark_bar(cornerRadius=3, color="#72b7b2")
        .encode(
            x=alt.X("first_ascents:Q", title="First ascents"),
            y=alt.Y("country:N", title=None, sort="-x"),
            tooltip=["country:N", alt.Tooltip("first_ascents:Q", format=",")],
        )
        .properties(height=300, title="Top 10 countries credited with first ascents")
    )
    country_chart
    return


if __name__ == "__main__":
    app.run()
