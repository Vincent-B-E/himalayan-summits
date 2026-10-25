-- Guard: every peak with a documented first-ascent country must appear in the
-- exploded country bridge. Fails if it returns rows.
select p.peak_id
from {{ ref('stg_peaks') }} p
where p.first_ascent_country is not null
  and not exists (
      select 1
      from {{ ref('bridge_peak_first_ascent_country') }} b
      where b.peak_id = p.peak_id
  )
