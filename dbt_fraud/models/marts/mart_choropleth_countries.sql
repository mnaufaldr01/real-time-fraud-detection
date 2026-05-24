select
    country,
    count(*) filter (where is_fraud) as fraud_count
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by country
having count(*) filter (where is_fraud) > 0
