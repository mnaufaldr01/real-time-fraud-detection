with bucketed as (
    select
        case
            when seconds_since_prev_txn is null then 'unknown'
            when seconds_since_prev_txn < 5 then '0-5s'
            when seconds_since_prev_txn < 30 then '5-30s'
            when seconds_since_prev_txn < 60 then '30-60s'
            when seconds_since_prev_txn < 300 then '1-5m'
            else '5m+'
        end as velocity_bucket,
        count(*) as fraud_count
    from {{ ref('int_velocity_fraud_events') }}
    where event_at >= current_timestamp - interval '30 days'
    group by 1
)

select velocity_bucket, fraud_count
from bucketed
order by
    case velocity_bucket
        when '0-5s' then 1
        when '5-30s' then 2
        when '30-60s' then 3
        when '1-5m' then 4
        when '5m+' then 5
        else 6
    end
