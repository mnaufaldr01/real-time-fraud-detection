select
    user_id,
    date_trunc('day', event_at)::date as report_date,
    count(*) filter (where is_fraud) as fraud_count
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '14 days'
group by user_id, date_trunc('day', event_at)::date
having count(*) filter (where is_fraud) > 0
