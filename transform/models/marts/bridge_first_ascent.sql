-- Many-to-many bridge: a peak to the expedition that first ascended it.
-- Replaces the old single peaks.first_ascent_expedition_id column so that one
-- expedition can be the first ascent of several peaks (e.g. SPH462101 is the
-- first ascent of both Sharphu IV and Nupchu).
select
    p.peak_id,
    e.expedition_sk
from {{ ref('stg_peaks') }} p
join {{ ref('stg_expeditions') }} e
    on e.expedition_id = p.first_ascent_expedition_id
where p.first_ascent_expedition_id is not null
