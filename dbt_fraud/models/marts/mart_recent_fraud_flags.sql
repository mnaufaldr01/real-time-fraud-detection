select
    e.transaction_id,
    e.user_id,
    e.event_at,
    e.amount_usd,
    e.country,
    rs.final_score,
    e.flag_reasons,
    e.scored_at
from {{ ref('int_scored_events') }} as e
left join {{ ref('stg_risk_scores') }} as rs
    on e.transaction_id = rs.transaction_id
where e.is_fraud = true
order by e.scored_at desc
limit 50
