select
    transaction_id::text as transaction_id,
    is_fraud,
    risk_tier,
    requires_user_confirmation,
    ml_prob,
    flag_reasons,
    ruleset_version,
    scored_at
from {{ source('fraud_oltp', 'fraud_flags') }}
