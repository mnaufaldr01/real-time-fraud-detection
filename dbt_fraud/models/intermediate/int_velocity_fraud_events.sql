select
    e.transaction_id,
    e.user_id,
    e.event_at,
    e.amount_usd,
    e.country,
    e.ip_country,
    e.is_fraud,
    e.is_velocity_fraud,
    e.seconds_since_prev_txn,
    e.hour_of_day,
    e.day_of_week
from {{ ref('int_scored_events') }} as e
where e.is_velocity_fraud = true
  and e.is_fraud = true
