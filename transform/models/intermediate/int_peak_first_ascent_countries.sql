-- Explodes the comma-separated first_ascent_country attribute into one row per
-- (peak, country), normalizing typos/variants through the country_aliases seed.
-- Sourced from stg_peaks (not bridge_first_ascent) so peaks with a documented
-- country but no linked first-ascent expedition are retained.

with source as (

    select
        peak_id,
        first_ascent_country
    from {{ ref('stg_peaks') }}
    where first_ascent_country is not null

),

split as (

    select
        s.peak_id,
        trim(t.token) as raw_country
    from source s
    cross join unnest(string_split(s.first_ascent_country, ',')) as t(token)
    where trim(t.token) <> ''

),

mapped as (

    select
        s.peak_id,
        coalesce(a.country, s.raw_country) as country
    from split s
    left join {{ ref('country_aliases') }} a
        on a.raw_country = s.raw_country

)

select distinct
    peak_id,
    country
from mapped
