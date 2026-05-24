with period as (
    select
        date_trunc('month', event_at)::date as report_date,
        count(*) as total_tx,
        count(*) filter (where is_fraud) as fraud_count,
        round(
            count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
            2
        ) as fraud_rate_pct
    from {{ ref('int_scored_events') }}
    where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
    group by date_trunc('month', event_at)::date
),

rolling as (
    select
        report_date,
        total_tx,
        fraud_count,
        fraud_rate_pct,
        avg(fraud_rate_pct) over (
            order by report_date
            rows between 2 preceding and current row
        ) as rolling_mean_rate,
        stddev(fraud_rate_pct) over (
            order by report_date
            rows between 2 preceding and current row
        ) as rolling_stddev_rate
    from period
)

select
    report_date,
    total_tx,
    fraud_count,
    fraud_rate_pct,
    case
        when fraud_rate_pct > rolling_mean_rate + 2 * coalesce(rolling_stddev_rate, 0)
            then true
        else false
    end as is_anomaly
from rolling
order by report_date
