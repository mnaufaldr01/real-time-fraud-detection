select
    transaction_id::text as transaction_id,
    user_id,
    timestamp as event_at,
    amount,
    currency,
    amount_usd,
    merchant_id,
    merchant_category,
    country,
    ip_country,
    payment_method,
    ingested_at
from {{ source('fraud_oltp', 'transactions') }}
