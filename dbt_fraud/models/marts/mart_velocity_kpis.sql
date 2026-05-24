select
    count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count,
    round(
        count(*) filter (where is_velocity_fraud and is_fraud) * 100.0
        / nullif(count(*) filter (where is_fraud), 0),
        2
    ) as velocity_fraud_share_pct,
    round(
        coalesce(sum(amount_usd) filter (where is_velocity_fraud and is_fraud), 0),
        2
    ) as sum_velocity_fraud_amount_usd,
    round(
        avg(seconds_since_prev_txn) filter (
            where is_velocity_fraud
              and is_fraud
              and seconds_since_prev_txn is not null
        )::numeric,
        1
    ) as avg_time_between_flagged_sec,
    count(distinct user_id) filter (where is_velocity_fraud and is_fraud) as unique_velocity_users
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '30 days'
