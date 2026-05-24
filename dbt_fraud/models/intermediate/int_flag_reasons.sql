select
    e.transaction_id,
    reason.value as reason
from {{ ref('int_scored_events') }} as e
cross join lateral jsonb_array_elements_text(e.flag_reasons) as reason(value)
where e.is_fraud = true
