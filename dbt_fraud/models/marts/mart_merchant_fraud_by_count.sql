select
    merchant_id,
    count(*) filter (where is_fraud) as fraud_count
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by merchant_id
having count(*) filter (where is_fraud) > 0
order by fraud_count desc
limit 15
