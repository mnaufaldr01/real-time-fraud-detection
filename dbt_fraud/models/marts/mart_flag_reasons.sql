select
    reason,
    count(*) as reason_count
from {{ ref('int_flag_reasons') }}
where reason not in (
    'HARD_DECLINE',
    'ML_STRONG_SUSPECT',
    'ML_REVIEW',
    'RULE_REVIEW',
    'HIGH_ANOMALY',
    'OUT_OF_SCOPE'
)
group by reason
order by reason_count desc
