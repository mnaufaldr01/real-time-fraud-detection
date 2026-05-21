"""Lightweight synthetic data profiling — outputs thresholds for rules."""

import json
import random
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PATH = PROJECT_ROOT / "docs" / "data_profile.md"

MERCHANT_CATEGORIES = [
    "5411", "5812", "5912", "4121", "5999", "5541", "6011", "7011", "7832", "7995"
]
COUNTRIES = ["US", "GB", "DE", "FR", "CA", "AU", "JP", "SG", "NL", "ES"]
NUM_ROWS = 10_000
FRAUD_RATE = 0.03


def generate_synthetic(n: int) -> list[dict]:
    rows = []
    users = [f"user_{i:05d}" for i in range(500)]
    base = datetime.now(timezone.utc) - timedelta(days=7)

    for i in range(n):
        user = random.choice(users)
        ts = base + timedelta(seconds=random.randint(0, 7 * 86400))
        amount = round(float(np.random.lognormal(3.5, 0.8)), 2)
        country = random.choice(COUNTRIES)

        rows.append(
            {
                "transaction_id": str(uuid.uuid4()),
                "user_id": user,
                "timestamp": ts,
                "amount": amount,
                "merchant_category": random.choice(MERCHANT_CATEGORIES),
                "country": country,
                "ip_country": country,
            }
        )

    # Inject fraud patterns
    fraud_count = int(n * FRAUD_RATE)
    for _ in range(fraud_count):
        idx = random.randint(0, n - 1)
        pattern = random.choice(["high_amount", "geo", "velocity"])
        if pattern == "high_amount":
            rows[idx]["amount"] = round(random.uniform(2000, 8000), 2)
        elif pattern == "geo":
            rows[idx]["ip_country"] = random.choice([c for c in COUNTRIES if c != rows[idx]["country"]])
        else:
            rows[idx]["user_id"] = "velocity_user"

    return rows


def profile(rows: list[dict]) -> dict:
    amounts = [r["amount"] for r in rows]
    p50, p95, p99 = np.percentile(amounts, [50, 95, 99])

    hourly_counts: dict[str, list] = defaultdict(list)
    user_hour: Counter = Counter()
    for r in rows:
        hour_key = r["timestamp"].strftime("%Y-%m-%d %H")
        user_hour[(r["user_id"], hour_key)] += 1

    for (user, hour), count in user_hour.items():
        hourly_counts[user].append(count)

    max_tx_per_hour = max(user_hour.values()) if user_hour else 0
    avg_tx_per_hour = np.mean(list(user_hour.values())) if user_hour else 0

    return {
        "row_count": len(rows),
        "amount_p50": round(float(p50), 2),
        "amount_p95": round(float(p95), 2),
        "amount_p99": round(float(p99), 2),
        "max_tx_per_user_hour": max_tx_per_hour,
        "avg_tx_per_user_hour": round(float(avg_tx_per_hour), 2),
        "merchant_category_cardinality": len(set(r["merchant_category"] for r in rows)),
        "country_cardinality": len(set(r["country"] for r in rows)),
        "fraud_injection_rate": FRAUD_RATE,
        "recommended_thresholds": {
            "HIGH_AMOUNT": f"amount > user P99 or global P99 ({round(float(p99), 2)})",
            "VELOCITY_1H": "> 5 tx / user / rolling 1h",
            "GEO_MISMATCH": "country != ip_country",
            "NEW_MERCHANT_HIGH": f"first-seen merchant + amount > P95 ({round(float(p95), 2)})",
            "FRAUD_SCORE_THRESHOLD": 70,
        },
    }


def write_markdown(stats: dict) -> None:
    lines = [
        "# Data Profile — Synthetic Transactions",
        "",
        f"Generated from {stats['row_count']:,} in-memory synthetic rows.",
        "",
        "## Amount Distribution",
        "",
        f"| Percentile | Value (USD) |",
        f"|------------|---------------|",
        f"| P50 | {stats['amount_p50']} |",
        f"| P95 | {stats['amount_p95']} |",
        f"| P99 | {stats['amount_p99']} |",
        "",
        "## Velocity",
        "",
        f"- Max transactions per user per hour: **{stats['max_tx_per_user_hour']}**",
        f"- Average transactions per user-hour bucket: **{stats['avg_tx_per_user_hour']}**",
        "",
        "## Cardinality",
        "",
        f"- Merchant categories: {stats['merchant_category_cardinality']}",
        f"- Countries: {stats['country_cardinality']}",
        "",
        "## Fraud Injection",
        "",
        f"- Target rate: **{stats['fraud_injection_rate'] * 100:.0f}%**",
        "",
        "## Recommended Thresholds",
        "",
        "```json",
        json.dumps(stats["recommended_thresholds"], indent=2),
        "```",
        "",
        "## Drift Baseline",
        "",
        f"- Baseline fraud rate for drift monitoring: {stats['fraud_injection_rate'] * 100:.1f}%",
        "- Re-run this script weekly and compare live fraud rate in `fraud_flags`.",
        "",
    ]
    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Profile written to {OUTPUT_PATH}")


def main():
    rows = generate_synthetic(NUM_ROWS)
    stats = profile(rows)
    write_markdown(stats)
    return stats


if __name__ == "__main__":
    main()
