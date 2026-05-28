/** Chart & UI palette — keep in sync with chart_template/style.css */
export const BRAND = {
  primary: "#E8621A",
  dark: "#C4511A",
  light: "#F59240",
  pale: "#FAC066",
} as const;

/** Consistent colors by metric type across all charts */
export const METRIC_COLORS = {
  count: BRAND.primary,
  amount: "#F5A623",
  rate: BRAND.dark,
} as const;

export type MetricKind = keyof typeof METRIC_COLORS;

export function metricKindForKey(key: string): MetricKind {
  if (key.endsWith("_usd") || /(?:^|_)amount(?:_|$)/i.test(key)) return "amount";
  if (key.endsWith("_pct") || /(?:^|_)(?:rate|share)(?:_|$)/i.test(key)) return "rate";
  return "count";
}

export function colorForMetricKey(key: string): string {
  return METRIC_COLORS[metricKindForKey(key)];
}

export const CHART_PALETTE = {
  orange: BRAND.primary,
  amber: "#F5A623",
  amberLight: BRAND.pale,
  amberDark: BRAND.dark,
  grid: "#EBEBEB",
  text: "#4A4A4A",
  textMuted: "#888888",
  legit: "#6B9E45",
  flagged: METRIC_COLORS.count,
  accent: METRIC_COLORS.count,
  warning: METRIC_COLORS.amount,
  secondary: BRAND.pale,
  white: "#FFFFFF",
  ...METRIC_COLORS,
} as const;

/** Distinct categorical colors for scatter chart countries (independent of brand palette) */
export const SCATTER_COUNTRY_COLORS = [
  "#4E79A7",
  "#F28E2B",
  "#E15759",
  "#76B7B2",
  "#59A14F",
  "#EDC948",
  "#B07AA1",
  "#FF9DA7",
  "#9C755F",
  "#86BCB6",
  "#499894",
  "#D37295",
  "#FABFD2",
  "#B6992D",
  "#79706E",
  "#D4A6C8",
];
