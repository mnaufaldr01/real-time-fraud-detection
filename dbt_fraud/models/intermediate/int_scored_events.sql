select
    t.transaction_id,
    t.user_id,
    t.event_at,
    t.amount,
    t.currency,
    t.amount_usd,
    t.merchant_id,
    t.merchant_category,
    t.country,
    t.ip_country,
    t.payment_method,
    coalesce(ff.is_fraud, false) as is_fraud,
    coalesce(ff.is_flagged, ff.is_fraud or coalesce(ff.requires_user_confirmation, false)) as is_flagged,
    ff.risk_tier,
    coalesce(ff.requires_user_confirmation, false) as requires_user_confirmation,
    ff.flag_reasons,
    rs.rule_score,
    rs.anomaly_score,
    rs.final_score,
    coalesce(ff.ml_prob, rs.ml_prob) as ml_prob,
    ff.scored_at,
    extract(hour from t.event_at)::int as hour_of_day,
    extract(dow from t.event_at)::int as day_of_week,
    extract(epoch from (
        t.event_at - lag(t.event_at) over (
            partition by t.user_id order by t.event_at
        )
    )) as seconds_since_prev_txn,
    coalesce(
        exists (
            select 1
            from jsonb_array_elements_text(ff.flag_reasons) as r(reason)
            where r.reason = 'VELOCITY_1H'
        ),
        false
    ) as is_velocity_fraud
from {{ ref('stg_transactions') }} as t
left join {{ ref('stg_fraud_flags') }} as ff
    on t.transaction_id = ff.transaction_id
left join {{ ref('stg_risk_scores') }} as rs
    on t.transaction_id = rs.transaction_id
where t.event_at >= current_timestamp - ({{ var('lookback_days') }} || ' days')::interval
