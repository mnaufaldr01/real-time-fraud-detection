# Data Profile — Synthetic Transactions

Generated from 10,000 in-memory synthetic rows.

## Amount Distribution

| Percentile | Value (USD) |
|------------|---------------|
| P50 | 33.14 |
| P95 | 131.71 |
| P99 | 397.2 |

## Velocity

- Max transactions per user per hour: **4**
- Average transactions per user-hour bucket: **1.06**

## Cardinality

- Merchant categories: 10
- Countries: 10

## Fraud Injection

- Target rate: **3%**

## Recommended Thresholds

```json
{
  "HIGH_AMOUNT": "amount > user P99 or global P99 (397.2)",
  "VELOCITY_1H": "> 5 tx / user / rolling 1h",
  "GEO_MISMATCH": "country != ip_country",
  "NEW_MERCHANT_HIGH": "first-seen merchant + amount > P95 (131.71)",
  "FRAUD_SCORE_THRESHOLD": 70
}
```

## Drift Baseline

- Baseline fraud rate for drift monitoring: 3.0%
- Re-run this script weekly and compare live fraud rate in `fraud_flags`.
