select
    transaction_id,
    user_id,
    country,
    amount_usd,
    seconds_since_prev_txn as velocity_seconds
from {{ ref('int_velocity_fraud_events') }}
where event_at >= current_timestamp - interval '30 days'
  and seconds_since_prev_txn is not null
