with daily as (
    select
        date_trunc('day', event_at)::date as report_date,
        count(*) as total_tx,
        count(*) filter (where is_fraud) as fraud_count,
        round(
            count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
            2
        ) as fraud_rate_pct
    from {{ ref('int_scored_events') }}
    where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
    group by date_trunc('day', event_at)::date
),

stats as (
    select
        avg(fraud_rate_pct) as mean_rate,
        stddev(fraud_rate_pct) as stddev_rate
    from daily
)

select
    d.report_date,
    d.total_tx,
    d.fraud_count,
    d.fraud_rate_pct,
    case
        when d.fraud_rate_pct > s.mean_rate + 2 * s.stddev_rate then true
        else false
    end as is_anomaly
from daily as d
cross join stats as s
order by d.report_date
