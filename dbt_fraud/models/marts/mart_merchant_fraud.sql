select
    merchant_id,
    count(*) as total_tx,
    count(*) filter (where is_fraud) as fraud_count,
    round(
        count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
        2
    ) as fraud_rate_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '30 days'
group by merchant_id
having count(*) filter (where is_fraud) > 0
order by fraud_count desc
limit 15
