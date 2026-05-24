select
    country,
    count(*) as total_tx,
    count(*) filter (where is_fraud) as fraud_count,
    round(
        count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
        2
    ) as fraud_rate_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '30 days'
group by country
having count(*) >= 3
order by fraud_rate_pct desc
