select
    count(*) as total_tx,
    count(*) filter (where is_fraud) as fraud_count,
    round(
        count(*) filter (where is_fraud) * 100.0 / nullif(count(*), 0),
        2
    ) as fraud_rate_pct,
    round(coalesce(sum(amount_usd) filter (where is_fraud), 0), 2) as sum_fraud_amount_usd,
    round(
        coalesce(sum(amount_usd) filter (where is_fraud), 0)
        / nullif(count(*) filter (where is_fraud), 0),
        2
    ) as avg_fraud_txn_value_usd,
    count(*) filter (where requires_user_confirmation) as review_queue_count,
    round(
        count(*) filter (where requires_user_confirmation) * 100.0
        / nullif(count(*) filter (where is_fraud), 0),
        2
    ) as flagged_to_review_ratio_pct
from {{ ref('int_scored_events') }}
where event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
