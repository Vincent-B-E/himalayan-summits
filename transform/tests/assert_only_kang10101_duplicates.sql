-- Guard: KANG10101 is the ONLY expedition_id allowed to repeat in the source.
-- Fails if any other duplicate business key appears. Returns rows on failure.
select expedition_id
from {{ ref('fct_expeditions') }}
group by expedition_id
having count(*) > 1
   and expedition_id <> 'KANG10101'
