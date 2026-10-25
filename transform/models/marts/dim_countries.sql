select distinct
    country
from {{ ref('int_peak_first_ascent_countries') }}
