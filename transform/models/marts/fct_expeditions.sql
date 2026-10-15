select
    expedition_sk,
    expedition_id,
    peak_id,
    year,
    season,
    basecamp_date,
    highpoint_date,
    termination_date,
    termination_reason,
    highpoint_metres,
    members_count,
    member_deaths,
    hired_staff,
    hired_staff_deaths,
    oxygen_used,
    trekking_agency
from {{ ref('stg_expeditions') }}
