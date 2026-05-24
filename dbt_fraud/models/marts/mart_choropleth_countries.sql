select
    country,
    total_tx,
    fraud_count,
    fraud_rate_pct
from {{ ref('mart_country_fraud_rate') }}
