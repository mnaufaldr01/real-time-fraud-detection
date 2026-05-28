export type Granularity = "Daily" | "Monthly" | "Yearly";

export interface DateFilter {
  year?: number;
  month?: number;
}

export interface DateDrilldown {
  year: number | null;
  month: number | null;
}

export interface MetaStatus {
  general_ready: boolean;
  velocity_ready: boolean;
  fingerprint: string | null;
  auto_refresh_seconds: number;
}

export interface GeneralKpis {
  total_tx?: number;
  flagged_count?: number;
  fraud_count?: number;
  fraud_rate_pct?: number;
  sum_fraud_amount_usd?: number;
  review_share_of_actions_pct?: number;
  review_share_of_flagged_pct?: number;
}

export interface VelocityKpis {
  velocity_fraud_count?: number;
  velocity_fraud_share_pct?: number;
  sum_velocity_fraud_amount_usd?: number;
  avg_time_between_flagged_sec?: number;
  unique_velocity_users?: number;
}

export interface CurrencyRow {
  currency: string;
  legitimate_count: number;
  flagged_count: number;
}

export interface TopUserRow {
  user_id: string;
  fraud_count: number;
  fraud_amount_usd: number;
}

export interface MerchantRow {
  merchant_id: string;
  fraud_count: number;
  fraud_amount_usd?: number;
  fraud_rate_pct?: number;
}

export interface CountryRow {
  country: string;
  fraud_count?: number;
  fraud_rate_pct?: number;
  velocity_fraud_count?: number;
  velocity_fraud_rate_pct?: number;
}

export interface FlagReasonRow {
  reason: string;
  reason_count: number;
}

export interface TrendRow {
  report_date: string;
  fraud_count: number;
  fraud_rate_pct: number;
  is_anomaly?: boolean;
  velocity_fraud_share_pct?: number;
}

export interface VelocityBucketRow {
  velocity_bucket: string;
  fraud_count: number;
}

export interface VelocityUserRow {
  user_id: string;
  velocity_fraud_count: number;
  velocity_fraud_amount_usd: number;
  avg_velocity_seconds: number;
}

export interface VelocityScatterRow {
  velocity_seconds: number;
  amount_usd: number;
  country: string;
  user_id: string;
  transaction_id: string;
}

export interface HeatmapRow {
  day_of_week: number;
  hour_of_day: number;
  velocity_fraud_count: number;
}

export interface IntervalRow {
  interval_bucket: string;
  interval_count: number;
}
