import type {
  CountryRow,
  CurrencyRow,
  FlagReasonRow,
  GeneralKpis,
  Granularity,
  HeatmapRow,
  IntervalRow,
  MerchantRow,
  MetaStatus,
  TopUserRow,
  TrendRow,
  VelocityBucketRow,
  VelocityKpis,
  VelocityScatterRow,
  VelocityUserRow,
} from "../types";

export const mockMeta: MetaStatus = {
  general_ready: true,
  velocity_ready: true,
  fingerprint: "demo-sample-v1",
  auto_refresh_seconds: 0,
};

export const mockGeneralKpis: GeneralKpis = {
  total_tx: 128_450,
  flagged_count: 4_820,
  fraud_count: 3_156,
  fraud_rate_pct: 2.46,
  sum_fraud_amount_usd: 1_842_350.75,
  review_share_of_actions_pct: 18.4,
};

export const mockVelocityKpis: VelocityKpis = {
  velocity_fraud_count: 892,
  velocity_fraud_share_pct: 28.3,
  sum_velocity_fraud_amount_usd: 412_880.5,
  avg_time_between_flagged_sec: 1.8,
  unique_velocity_users: 214,
};

export const mockCurrency: CurrencyRow[] = [
  { currency: "USD", legitimate_count: 62_400, flagged_count: 1_820 },
  { currency: "EUR", legitimate_count: 28_100, flagged_count: 940 },
  { currency: "GBP", legitimate_count: 14_200, flagged_count: 510 },
  { currency: "NGN", legitimate_count: 8_900, flagged_count: 620 },
  { currency: "JPY", legitimate_count: 6_200, flagged_count: 280 },
];

export const mockTopUsers: TopUserRow[] = [
  { user_id: "U-10482", fraud_count: 142, fraud_amount_usd: 98_420 },
  { user_id: "U-22901", fraud_count: 118, fraud_amount_usd: 76_300 },
  { user_id: "U-8834", fraud_count: 97, fraud_amount_usd: 54_120 },
  { user_id: "U-55102", fraud_count: 86, fraud_amount_usd: 41_880 },
  { user_id: "U-33019", fraud_count: 74, fraud_amount_usd: 38_650 },
  { user_id: "U-77210", fraud_count: 68, fraud_amount_usd: 29_400 },
  { user_id: "U-90144", fraud_count: 61, fraud_amount_usd: 22_150 },
  { user_id: "U-12055", fraud_count: 55, fraud_amount_usd: 18_900 },
  { user_id: "U-44881", fraud_count: 49, fraud_amount_usd: 15_220 },
  { user_id: "U-66723", fraud_count: 44, fraud_amount_usd: 12_480 },
  { user_id: "U-31209", fraud_count: 38, fraud_amount_usd: 9_840 },
  { user_id: "U-59001", fraud_count: 32, fraud_amount_usd: 7_120 },
];

export const mockMerchantsByCount: MerchantRow[] = [
  { merchant_id: "M-RET-001", fraud_count: 420, fraud_amount_usd: 210_500 },
  { merchant_id: "M-TRV-882", fraud_count: 318, fraud_amount_usd: 185_200 },
  { merchant_id: "M-DIG-441", fraud_count: 276, fraud_amount_usd: 92_400 },
  { merchant_id: "M-FIN-119", fraud_count: 241, fraud_amount_usd: 156_800 },
  { merchant_id: "M-RTL-903", fraud_count: 198, fraud_amount_usd: 48_300 },
  { merchant_id: "M-GAM-552", fraud_count: 172, fraud_amount_usd: 64_100 },
  { merchant_id: "M-SVC-220", fraud_count: 145, fraud_amount_usd: 31_900 },
  { merchant_id: "M-TRV-331", fraud_count: 128, fraud_amount_usd: 88_600 },
  { merchant_id: "M-DIG-772", fraud_count: 112, fraud_amount_usd: 27_400 },
  { merchant_id: "M-FOD-881", fraud_count: 98, fraud_amount_usd: 19_200 },
];

export const mockMerchantsByRate: MerchantRow[] = [
  { merchant_id: "M-GAM-552", fraud_count: 172, fraud_rate_pct: 12.8 },
  { merchant_id: "M-DIG-441", fraud_count: 276, fraud_rate_pct: 9.4 },
  { merchant_id: "M-TRV-882", fraud_count: 318, fraud_rate_pct: 8.1 },
  { merchant_id: "M-FIN-119", fraud_count: 241, fraud_rate_pct: 6.9 },
  { merchant_id: "M-RET-001", fraud_count: 420, fraud_rate_pct: 5.2 },
  { merchant_id: "M-RTL-903", fraud_count: 198, fraud_rate_pct: 4.8 },
  { merchant_id: "M-SVC-220", fraud_count: 145, fraud_rate_pct: 3.9 },
  { merchant_id: "M-TRV-331", fraud_count: 128, fraud_rate_pct: 3.2 },
  { merchant_id: "M-DIG-772", fraud_count: 112, fraud_rate_pct: 2.7 },
  { merchant_id: "M-FOD-881", fraud_count: 98, fraud_rate_pct: 2.1 },
];

export const mockCountriesByCount: CountryRow[] = [
  { country: "US", fraud_count: 820 },
  { country: "NG", fraud_count: 540 },
  { country: "GB", fraud_count: 410 },
  { country: "DE", fraud_count: 380 },
  { country: "FR", fraud_count: 290 },
  { country: "CA", fraud_count: 245 },
  { country: "BR", fraud_count: 220 },
  { country: "IN", fraud_count: 198 },
  { country: "AU", fraud_count: 165 },
  { country: "MX", fraud_count: 142 },
];

export const mockCountriesByRate: CountryRow[] = [
  { country: "NG", fraud_rate_pct: 8.9 },
  { country: "BR", fraud_rate_pct: 6.2 },
  { country: "MX", fraud_rate_pct: 5.4 },
  { country: "IN", fraud_rate_pct: 4.8 },
  { country: "US", fraud_rate_pct: 3.1 },
  { country: "GB", fraud_rate_pct: 2.9 },
  { country: "DE", fraud_rate_pct: 2.6 },
  { country: "FR", fraud_rate_pct: 2.4 },
  { country: "CA", fraud_rate_pct: 2.1 },
  { country: "AU", fraud_rate_pct: 1.9 },
];

export const mockFlagReasons: FlagReasonRow[] = [
  { reason: "velocity_threshold", reason_count: 892 },
  { reason: "amount_anomaly", reason_count: 756 },
  { reason: "geo_mismatch", reason_count: 612 },
  { reason: "merchant_risk", reason_count: 488 },
  { reason: "device_fingerprint", reason_count: 394 },
  { reason: "model_score_high", reason_count: 318 },
  { reason: "repeat_decline", reason_count: 256 },
];

export const mockVelocityBuckets: VelocityBucketRow[] = [
  { velocity_bucket: "0-5s", fraud_count: 512 },
  { velocity_bucket: "6-15s", fraud_count: 198 },
  { velocity_bucket: "16-30s", fraud_count: 94 },
  { velocity_bucket: "31-60s", fraud_count: 58 },
  { velocity_bucket: "60s+", fraud_count: 30 },
];

export const mockVelocityUsers: VelocityUserRow[] = [
  { user_id: "U-10482", velocity_fraud_count: 48, velocity_fraud_amount_usd: 42_100, avg_velocity_seconds: 0.8 },
  { user_id: "U-22901", velocity_fraud_count: 41, velocity_fraud_amount_usd: 31_200, avg_velocity_seconds: 1.1 },
  { user_id: "U-8834", velocity_fraud_count: 36, velocity_fraud_amount_usd: 28_400, avg_velocity_seconds: 0.6 },
  { user_id: "U-55102", velocity_fraud_count: 29, velocity_fraud_amount_usd: 19_800, avg_velocity_seconds: 1.4 },
  { user_id: "U-33019", velocity_fraud_count: 24, velocity_fraud_amount_usd: 15_600, avg_velocity_seconds: 0.9 },
  { user_id: "U-77210", velocity_fraud_count: 21, velocity_fraud_amount_usd: 12_400, avg_velocity_seconds: 1.2 },
  { user_id: "U-90144", velocity_fraud_count: 18, velocity_fraud_amount_usd: 9_800, avg_velocity_seconds: 0.7 },
  { user_id: "U-12055", velocity_fraud_count: 15, velocity_fraud_amount_usd: 8_200, avg_velocity_seconds: 1.0 },
  { user_id: "U-44881", velocity_fraud_count: 12, velocity_fraud_amount_usd: 6_400, avg_velocity_seconds: 1.6 },
  { user_id: "U-66723", velocity_fraud_count: 10, velocity_fraud_amount_usd: 4_900, avg_velocity_seconds: 0.5 },
];

export const mockVelocityCountriesCount: CountryRow[] = [
  { country: "US", velocity_fraud_count: 210 },
  { country: "NG", velocity_fraud_count: 168 },
  { country: "GB", velocity_fraud_count: 98 },
  { country: "DE", velocity_fraud_count: 82 },
  { country: "FR", velocity_fraud_count: 64 },
  { country: "CA", velocity_fraud_count: 52 },
  { country: "BR", velocity_fraud_count: 48 },
  { country: "IN", velocity_fraud_count: 41 },
];

export const mockVelocityCountriesRate: CountryRow[] = [
  { country: "NG", velocity_fraud_rate_pct: 14.2 },
  { country: "BR", velocity_fraud_rate_pct: 9.8 },
  { country: "US", velocity_fraud_rate_pct: 6.4 },
  { country: "GB", velocity_fraud_rate_pct: 5.1 },
  { country: "DE", velocity_fraud_rate_pct: 4.6 },
  { country: "IN", velocity_fraud_rate_pct: 4.2 },
  { country: "FR", velocity_fraud_rate_pct: 3.8 },
  { country: "CA", velocity_fraud_rate_pct: 3.2 },
];

export const mockRepeatInterval: IntervalRow[] = [
  { interval_bucket: "0-1s", interval_count: 384 },
  { interval_bucket: "1-2s", interval_count: 198 },
  { interval_bucket: "2-5s", interval_count: 142 },
  { interval_bucket: "5-10s", interval_count: 86 },
  { interval_bucket: "10-30s", interval_count: 52 },
  { interval_bucket: "30s+", interval_count: 30 },
];

const SCATTER_COUNTRIES = ["US", "NG", "GB", "DE", "FR", "CA", "BR", "IN"];

function buildScatter(): VelocityScatterRow[] {
  const rows: VelocityScatterRow[] = [];
  let id = 1;
  for (let i = 0; i < 220; i += 1) {
    const country = SCATTER_COUNTRIES[i % SCATTER_COUNTRIES.length]!;
    const velocity = Math.pow(Math.random(), 2.2) * 1.8;
    const amount = 20 + Math.pow(Math.random(), 1.4) * 4_800;
    rows.push({
      transaction_id: `TX-DEMO-${String(id++).padStart(5, "0")}`,
      user_id: `U-${10000 + (i % 40)}`,
      country,
      velocity_seconds: Math.round(velocity * 1000) / 1000,
      amount_usd: Math.round(amount * 100) / 100,
    });
  }
  return rows;
}

export const mockScatter = buildScatter();

function buildHeatmap(): HeatmapRow[] {
  const rows: HeatmapRow[] = [];
  for (let day = 0; day < 7; day += 1) {
    for (let hour = 0; hour < 24; hour += 1) {
      const peak = hour >= 9 && hour <= 22 ? 1 : 0.25;
      const weekend = day === 0 || day === 6 ? 0.7 : 1;
      const base = Math.round((4 + Math.sin(hour / 3) * 3) * peak * weekend);
      rows.push({
        day_of_week: day,
        hour_of_day: hour,
        velocity_fraud_count: base + (hour + day) % 5,
      });
    }
  }
  return rows;
}

export const mockHeatmap = buildHeatmap();

function buildYearlyTrends(baseCount: number, share = false): TrendRow[] {
  return [2022, 2023, 2024, 2025].map((year, index) => ({
    report_date: `${year}-01-01`,
    fraud_count: baseCount + index * 180 + (year % 3) * 40,
    fraud_rate_pct: 2.0 + index * 0.18,
    ...(share ? { velocity_fraud_share_pct: 22 + index * 2.4 } : {}),
  }));
}

function buildMonthlyTrends(year: number, baseCount: number, share = false): TrendRow[] {
  return Array.from({ length: 12 }, (_, month) => ({
    report_date: `${year}-${String(month + 1).padStart(2, "0")}-01`,
    fraud_count: baseCount + month * 28 + (month % 4) * 15,
    fraud_rate_pct: 2.1 + month * 0.04,
    ...(share ? { velocity_fraud_share_pct: 24 + month * 0.6 } : {}),
  }));
}

function buildDailyTrends(year: number, month: number, baseCount: number, share = false): TrendRow[] {
  const days = new Date(year, month, 0).getDate();
  return Array.from({ length: days }, (_, day) => ({
    report_date: `${year}-${String(month).padStart(2, "0")}-${String(day + 1).padStart(2, "0")}`,
    fraud_count: baseCount + (day % 7) * 12 + Math.floor(day / 3),
    fraud_rate_pct: 2.0 + (day % 10) * 0.08,
    ...(share ? { velocity_fraud_share_pct: 26 + (day % 14) * 0.5 } : {}),
  }));
}

export function mockGeneralTrends(granularity: Granularity): TrendRow[] {
  if (granularity === "Yearly") return buildYearlyTrends(680);
  if (granularity === "Monthly") return buildMonthlyTrends(2024, 520);
  return buildDailyTrends(2024, 6, 18);
}

export function mockVelocityShareTrend(granularity: Granularity): TrendRow[] {
  if (granularity === "Yearly") return buildYearlyTrends(680, true);
  if (granularity === "Monthly") return buildMonthlyTrends(2024, 520, true);
  return buildDailyTrends(2024, 6, 18, true);
}

export function mockVelocityTrends(granularity: Granularity): TrendRow[] {
  return mockGeneralTrends(granularity).map((row) => ({
    ...row,
    fraud_count: Math.round(row.fraud_count * 0.28),
    fraud_rate_pct: row.fraud_rate_pct * 0.9,
  }));
}
