with members as (

    select * from {{ ref('stg_members') }}

),

expeditions as (

    -- (expedition_id, year) is unique, so this resolves the KANG10101
    -- collision to the correct expedition surrogate key.
    select expedition_id, year, expedition_sk from {{ ref('stg_expeditions') }}

)

select
    m.member_sk,
    m.member_id,
    e.expedition_sk,
    m.sex,
    m.age,
    m.citizenship,
    m.expedition_role,
    m.hired,
    m.highpoint_metres,
    m.success,
    m.solo,
    m.oxygen_used,
    m.died,
    m.death_cause,
    m.death_height_metres,
    m.injured,
    m.injury_type,
    m.injury_height_metres
from members m
left join expeditions e
    on m.expedition_id = e.expedition_id
   and m.year = e.year
