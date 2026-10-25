-- Many-to-many bridge: one row per (peak, country) credited with its first
-- ascent. Explodes the former comma-separated dim_peaks.first_ascent_country
-- so grouping by a single country aggregates correctly.
select
    peak_id,
    country
from {{ ref('int_peak_first_ascent_countries') }}
