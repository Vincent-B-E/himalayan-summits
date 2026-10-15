with source as (

    select * from {{ source('raw', 'peaks') }}

)

select
    peak_id,
    peak_name,
    {{ to_null('peak_alternative_name') }}       as peak_alternative_name,
    {{ as_int('height_metres') }}                as height_metres,
    climbing_status,
    {{ as_int('first_ascent_year') }}            as first_ascent_year,
    {{ to_null('first_ascent_country') }}        as first_ascent_country,
    {{ to_null('first_ascent_expedition_id') }}  as first_ascent_expedition_id
from source
