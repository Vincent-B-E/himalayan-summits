-- Optional N:1 link: each peak has at most one first-ascent expedition, while
-- one expedition may be credited with several peaks (e.g. SPH462101 is the
-- first ascent of both Sharphu IV and Nupchu). Materialized as a link model so
-- downstream consumers get a resolved expedition_sk without dim_peaks carrying
-- a foreign key into fct_expeditions.
--
-- Caveat: the join uses expedition_id only. It is not collision-proof for the
-- KANG10101 business key (no first-ascent peak points at it today). Year is not
-- a reliable disambiguator here: first_ascent_year disagrees with the expedition
-- year for CBAM, GHUS and SPH2.
select
    p.peak_id,
    e.expedition_sk
from {{ ref('stg_peaks') }} p
join {{ ref('stg_expeditions') }} e
    on e.expedition_id = p.first_ascent_expedition_id
where p.first_ascent_expedition_id is not null
