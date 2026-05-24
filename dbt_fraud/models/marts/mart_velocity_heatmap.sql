select
    hour_of_day,
    day_of_week,
    count(*) as velocity_fraud_count
from {{ ref('int_velocity_fraud_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
group by hour_of_day, day_of_week
order by day_of_week, hour_of_day
