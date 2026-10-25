select
    peak_id,
    peak_name,
    peak_alternative_name,
    height_metres,
    climbing_status,
    first_ascent_year
from {{ ref('stg_peaks') }}
