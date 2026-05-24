with monthly as (
    select
        date_trunc('month', event_at)::date as report_month,
        count(*) as total_tx,
        count(*) filter (where is_fraud) as fraud_count,
        round(
            count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
            2
        ) as fraud_rate_pct
    from {{ ref('int_scored_events') }}
    where event_at >= current_timestamp - interval '365 days'
    group by date_trunc('month', event_at)::date
)

select
    report_month,
    total_tx,
    fraud_count,
    fraud_rate_pct
from monthly
order by report_month
