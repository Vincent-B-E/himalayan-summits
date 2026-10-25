-- Guard: raw typo/variant tokens must never reach dim_countries; they should be
-- normalized by the country_aliases seed. Fails if it returns rows.
select c.country
from {{ ref('dim_countries') }} c
inner join {{ ref('country_aliases') }} a
    on a.raw_country = c.country
