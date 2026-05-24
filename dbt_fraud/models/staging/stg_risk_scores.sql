select
    transaction_id::text as transaction_id,
    rule_score,
    anomaly_score,
    final_score,
    ml_prob,
    ruleset_version,
    model_version,
    scored_at
from {{ source('fraud_oltp', 'risk_scores') }}
