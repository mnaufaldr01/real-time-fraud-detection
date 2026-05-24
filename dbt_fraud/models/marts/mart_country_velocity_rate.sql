select
    country,
    count(*) as total_tx,
    count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count,
    round(
        count(*) filter (where is_velocity_fraud and is_fraud) * 100.0
        / nullif(count(*), 0),
        2
    ) as velocity_fraud_rate_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by country
having count(*) >= 3
order by velocity_fraud_rate_pct desc
