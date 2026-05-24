select
    country,
    count(*) filter (where is_velocity_fraud and is_fraud) as velocity_fraud_count
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - interval '30 days'
group by country
having count(*) filter (where is_velocity_fraud and is_fraud) > 0
order by velocity_fraud_count desc
limit 15
