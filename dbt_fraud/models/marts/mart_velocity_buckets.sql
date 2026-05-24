with bucketed as (
    select
        case
            when seconds_since_prev_txn is null then 'unknown'
            when seconds_since_prev_txn <= 5 then '0-5s'
            when seconds_since_prev_txn <= 15 then '6-15s'
            when seconds_since_prev_txn <= 30 then '16-30s'
            when seconds_since_prev_txn <= 60 then '31-60s'
            else '60s+'
        end as velocity_bucket,
        count(*) as fraud_count
    from {{ ref('int_velocity_fraud_events') }}
    where event_at >= current_timestamp - interval '30 days'
    group by 1
)

select velocity_bucket, fraud_count
from bucketed
where velocity_bucket != 'unknown'
order by
    case velocity_bucket
        when '0-5s' then 1
        when '6-15s' then 2
        when '16-30s' then 3
        when '31-60s' then 4
        when '60s+' then 5
        else 6
    end
