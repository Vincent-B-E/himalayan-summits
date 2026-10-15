-- Guard: the KANG10101 id collision (1910 vs 2010) must keep BOTH
-- expeditions. The surrogate key is the fix; this catches any future
-- accidental de-duplication of the business key. Fails if it returns rows.
select expedition_id
from {{ ref('fct_expeditions') }}
where expedition_id = 'KANG10101'
group by expedition_id
having count(*) <> 2
