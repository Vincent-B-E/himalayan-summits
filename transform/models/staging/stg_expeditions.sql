with source as (

    select * from {{ source('raw', 'expeditions') }}

)

select
    expedition_id,
    case when peak_id = 'SPHU' then 'SPHN' else peak_id end as peak_id,
    {{ as_int('year') }}                         as year,
    {{ to_null('season') }}                      as season,
    {{ as_date('basecamp_date') }}               as basecamp_date,
    {{ as_date('highpoint_date') }}              as highpoint_date,
    {{ as_date('termination_date') }}            as termination_date,
    {{ to_null('termination_reason') }}          as termination_reason,
    {{ as_int('highpoint_metres') }}             as highpoint_metres,
    {{ as_int('members') }}                      as members_count,
    {{ as_int('member_deaths') }}                as member_deaths,
    {{ as_int('hired_staff') }}                  as hired_staff,
    {{ as_int('hired_staff_deaths') }}           as hired_staff_deaths,
    oxygen_used,
    {{ to_null('trekking_agency') }}             as trekking_agency,

    -- Surrogate key. expedition_id is NOT unique (KANG10101 collides across
    -- 1910 and 2010); adding `year` makes the hash unique and deterministic.
    {{ dbt_utils.generate_surrogate_key(['expedition_id', 'year']) }} as expedition_sk
from source
