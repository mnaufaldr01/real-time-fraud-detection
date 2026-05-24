select
    e.user_id,
    e.transaction_id,
    e.event_at,
    e.amount_usd,
    e.seconds_since_prev_txn as repeat_interval_seconds
from {{ ref('int_velocity_fraud_events') }} as e
where e.seconds_since_prev_txn is not null
  and e.seconds_since_prev_txn >= 0
