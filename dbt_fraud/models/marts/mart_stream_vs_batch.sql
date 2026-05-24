with latest_batch as (
    select
        rs.transaction_id,
        rs.final_score as stream_score,
        rsh.final_score as batch_score,
        abs(rs.final_score - rsh.final_score) as delta,
        row_number() over (
            partition by rs.transaction_id
            order by rsh.scored_at desc
        ) as rn
    from {{ ref('stg_risk_scores') }} as rs
    inner join {{ source('fraud_oltp', 'risk_scores_history') }} as rsh
        on rs.transaction_id = rsh.transaction_id::text
    where rsh.scored_at >= current_timestamp - interval '7 days'
)

select
    transaction_id,
    stream_score,
    batch_score,
    delta
from latest_batch
where rn = 1
order by delta desc
limit 20
