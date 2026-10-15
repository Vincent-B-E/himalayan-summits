with source as (

    -- peak_id / peak_name are denormalized copies of the expedition's peak and
    -- are dropped here; reach the peak via expedition -> peak instead.
    select * from {{ source('raw', 'members') }}

)

select
    member_id,
    expedition_id,
    {{ as_int('year') }}                          as year,
    {{ to_null('season') }}                       as season,
    {{ to_null('sex') }}                          as sex,
    {{ as_int('age') }}                           as age,
    {{ to_null('citizenship') }}                  as citizenship,
    {{ to_null('expedition_role') }}              as expedition_role,
    hired,
    {{ as_int('highpoint_metres') }}              as highpoint_metres,
    success,
    solo,
    oxygen_used,
    died,
    {{ to_null('death_cause') }}                  as death_cause,
    {{ as_int('death_height_metres') }}           as death_height_metres,
    injured,
    {{ to_null('injury_type') }}                  as injury_type,
    {{ as_int('injury_height_metres') }}          as injury_height_metres,

    -- `year` is used transiently to disambiguate members of the two colliding
    -- KANG10101 expeditions before it is dropped downstream in fct_members.
    {{ dbt_utils.generate_surrogate_key(['member_id', 'expedition_id', 'year']) }} as member_sk
from source
