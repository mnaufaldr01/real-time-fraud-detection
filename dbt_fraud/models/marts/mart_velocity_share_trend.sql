with daily as (
    select
        date_trunc('day', event_at)::date as report_date,
        count(*) filter (where is_fraud) as total_fraud_count,
        count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count
    from {{ ref('int_scored_events') }}
    where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
    group by date_trunc('day', event_at)::date
)

select
    report_date,
    total_fraud_count,
    velocity_fraud_count,
    round(
        velocity_fraud_count * 100.0 / nullif(total_fraud_count, 0),
        2
    ) as velocity_fraud_share_pct
from daily
order by report_date
