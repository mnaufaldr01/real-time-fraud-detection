with user_velocity as (
    select
        user_id,
        count(*) as velocity_fraud_count,
        coalesce(sum(amount_usd), 0) as velocity_fraud_amount_usd,
        round(avg(seconds_since_prev_txn)::numeric, 1) as avg_velocity_seconds
    from {{ ref('int_velocity_fraud_events') }}
    where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
    group by user_id
)

select
    user_id,
    velocity_fraud_count,
    velocity_fraud_amount_usd,
    avg_velocity_seconds
from user_velocity
order by velocity_fraud_count desc, velocity_fraud_amount_usd desc
limit 15
