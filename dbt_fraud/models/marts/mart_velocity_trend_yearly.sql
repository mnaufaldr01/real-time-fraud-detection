with period as (
    select
        date_trunc('year', event_at)::date as report_date,
        count(*) as total_tx,
        count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count,
        round(
            count(*) filter (where is_velocity_fraud and is_fraud) * 100.0
            / nullif(count(*), 0),
            2
        ) as velocity_fraud_rate_pct
    from {{ ref('int_scored_events') }}
    group by date_trunc('year', event_at)::date
)

select
    report_date,
    total_tx,
    velocity_fraud_count as fraud_count,
    velocity_fraud_rate_pct as fraud_rate_pct,
    false as is_anomaly
from period
order by report_date
