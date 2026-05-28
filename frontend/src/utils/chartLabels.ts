/** Stakeholder-friendly labels for chart titles, axes, legends, and tooltips. */

const METRIC_LABELS: Record<string, string> = {
  fraud_count: "Fraud-flagged transactions",
  fraud_amount_usd: "Fraud-flagged amount",
  fraud_rate_pct: "Fraud rate",
  flagged_count: "Flagged transactions",
  legitimate_count: "Legitimate transactions",
  reason_count: "Times rule triggered",
  velocity_fraud_count: "Velocity-flagged transactions",
  velocity_fraud_amount_usd: "Velocity-flagged amount",
  velocity_fraud_rate_pct: "Velocity fraud rate",
  velocity_fraud_share_pct: "Share of fraud from velocity",
  interval_count: "Consecutive flag pairs",
};

const CATEGORY_LABELS: Record<string, string> = {
  user_id: "User",
  merchant_id: "Merchant",
  country: "Country",
  currency: "Currency",
  reason: "Flag reason",
  velocity_bucket: "Time between transactions",
  interval_bucket: "Time between flags",
};

const AXIS_VALUE_LABELS: Record<string, string> = {
  fraud_count: "Number of fraud-flagged transactions",
  fraud_amount_usd: "Fraud-flagged amount (USD)",
  fraud_rate_pct: "Fraud rate (%)",
  flagged_count: "Number of flagged transactions",
  legitimate_count: "Number of transactions",
  reason_count: "Number of flags",
  velocity_fraud_count: "Number of velocity-flagged transactions",
  velocity_fraud_amount_usd: "Velocity-flagged amount (USD)",
  velocity_fraud_rate_pct: "Velocity fraud rate (%)",
  velocity_fraud_share_pct: "Share of fraud from velocity (%)",
  interval_count: "Number of transaction pairs",
};

export function metricLabel(dataKey: string): string {
  return METRIC_LABELS[dataKey] ?? fallbackLabel(dataKey);
}

export function categoryLabel(dataKey: string): string {
  return CATEGORY_LABELS[dataKey] ?? fallbackLabel(dataKey);
}

export function axisValueLabel(dataKey: string): string {
  return AXIS_VALUE_LABELS[dataKey] ?? metricLabel(dataKey);
}

function fallbackLabel(key: string): string {
  return key
    .replace(/_usd$|_pct$/i, "")
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

/** Chart card titles — insight-oriented phrasing for stakeholders. */
export const CHART_TITLES = {
  general: {
    currency: "Transactions by currency: legitimate vs flagged",
    usersByCount: "Users with the most fraud-flagged transactions",
    usersByAmount: "Users with the highest fraud-flagged amounts",
    merchantsByCount: "Merchants with the most fraud-flagged transactions",
    merchantsByAmount: "Merchants with the highest fraud amounts",
    merchantsByRate: "Merchants with the highest fraud rate",
    countriesByCount: "Countries with the most fraud-flagged transactions",
    countriesByRate: "Countries with the highest fraud rate",
    flagReasons: "Why transactions were flagged (by rule)",
    fraudTrend: "Fraud-flagged transactions over time",
  },
  velocity: {
    buckets: "How quickly flagged transactions arrive",
    usersByCount: "Users with the most velocity-flagged transactions",
    usersByAmount: "Users with the highest velocity-flagged amounts",
    countriesByCount: "Countries with the most velocity-flagged transactions",
    countriesByRate: "Countries with the highest velocity fraud rate",
    scatter: "Transaction amount vs time between consecutive flags",
    shareTrend: "What share of all fraud comes from velocity rules",
    heatmap: "When velocity flags happen (day and hour)",
    intervals: "Gap between back-to-back velocity flags",
    trend: "Velocity-flagged transactions over time",
  },
} as const;
