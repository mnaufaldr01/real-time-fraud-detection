with user_totals as (
    select
        user_id,
        count(*) filter (where is_fraud) as fraud_count,
        coalesce(sum(amount_usd) filter (where is_fraud), 0) as fraud_amount_usd
    from {{ ref('int_scored_events') }}
    where event_at >= current_timestamp - interval '30 days'
    group by user_id
    having count(*) filter (where is_fraud) > 0
),

ranked as (
    select
        user_id,
        fraud_count,
        fraud_amount_usd,
        row_number() over (order by fraud_count desc, fraud_amount_usd desc) as rank_by_count
    from user_totals
)

select
    r.user_id,
    r.fraud_count,
    r.fraud_amount_usd,
    r.rank_by_count
from ranked as r
where r.rank_by_count <= 15
order by r.rank_by_count
