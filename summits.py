import marimo

__generated_with = "0.24.2"
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
    return expeditions_df, members_df, peaks_df


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


if __name__ == "__main__":
    app.run()
