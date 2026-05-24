select
    country,
    count(*) filter (where is_fraud) as fraud_count,
    coalesce(sum(amount_usd) filter (where is_fraud), 0) as fraud_amount_usd
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by country
order by fraud_count desc
limit 15
