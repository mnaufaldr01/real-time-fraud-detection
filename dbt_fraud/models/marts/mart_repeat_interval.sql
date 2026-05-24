with bucketed as (
    select
        case
            when repeat_interval_seconds < 1 then '0-1s'
            when repeat_interval_seconds < 2 then '1-2s'
            when repeat_interval_seconds < 3 then '2-3s'
            when repeat_interval_seconds < 4 then '3-4s'
            when repeat_interval_seconds < 5 then '4-5s'
            when repeat_interval_seconds < 10 then '5-10s'
            when repeat_interval_seconds < 30 then '10-30s'
            when repeat_interval_seconds < 60 then '30-60s'
            when repeat_interval_seconds < 300 then '1-5m'
            else '5m+'
        end as interval_bucket,
        count(*) as interval_count
    from {{ ref('int_velocity_repeat_intervals') }}
    where event_at >= current_timestamp - interval '30 days'
    group by 1
)

select interval_bucket, interval_count
from bucketed
order by
    case interval_bucket
        when '0-1s' then 1
        when '1-2s' then 2
        when '2-3s' then 3
        when '3-4s' then 4
        when '4-5s' then 5
        when '5-10s' then 6
        when '10-30s' then 7
        when '30-60s' then 8
        when '1-5m' then 9
        else 10
    end
