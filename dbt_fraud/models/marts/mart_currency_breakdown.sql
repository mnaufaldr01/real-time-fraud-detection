select
    currency,
    count(*) filter (where not is_fraud) as legitimate_count,
    count(*) filter (where is_fraud) as flagged_count,
    count(*) as total_count,
    round(
        count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
        2
    ) as fraud_rate_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '30 days'
group by currency
order by total_count desc
