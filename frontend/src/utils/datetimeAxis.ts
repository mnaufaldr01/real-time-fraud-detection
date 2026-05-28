import type { DateDrilldown, Granularity, TrendRow } from "../api/types";

export interface PreparedTrendRow {
  report_date: string;
  fraud_count: number | null;
  fraud_rate_pct: number | null;
  velocity_fraud_share_pct?: number | null;
  is_anomaly?: boolean;
  tooltipLabel: string;
  hasData: boolean;
}

const MONTH_YEAR = new Intl.DateTimeFormat("en-US", { month: "short", year: "numeric" });
const FULL_DATE = new Intl.DateTimeFormat("en-US", {
  month: "short",
  day: "numeric",
  year: "numeric",
});
const YEAR = new Intl.DateTimeFormat("en-US", { year: "numeric" });

export function parseReportDate(value: string): Date {
  const normalized = value.includes("T") ? value : `${value}T00:00:00`;
  return new Date(normalized);
}

export function formatMonthYear(date: Date): string {
  return MONTH_YEAR.format(date);
}

export function formatFullDate(date: Date): string {
  return FULL_DATE.format(date);
}

export function formatYear(date: Date): string {
  return YEAR.format(date);
}

function tooltipLabelFor(date: Date, granularity: Granularity): string {
  switch (granularity) {
    case "Daily":
      return formatFullDate(date);
    case "Monthly":
      return formatMonthYear(date);
    case "Yearly":
      return formatYear(date);
  }
}

function axisLabelFor(date: Date, granularity: Granularity): string {
  switch (granularity) {
    case "Daily":
    case "Monthly":
      return formatMonthYear(date);
    case "Yearly":
      return formatYear(date);
  }
}

function monthKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}`;
}

function padYearlyRows(rows: PreparedTrendRow[]): PreparedTrendRow[] {
  const years = rows.map((row) => parseReportDate(row.report_date).getFullYear());
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const span = maxYear - minYear + 1;
  const endYear = span >= 3 ? maxYear : minYear + 2;

  const byYear = new Map<number, PreparedTrendRow>();
  for (const row of rows) {
    byYear.set(parseReportDate(row.report_date).getFullYear(), row);
  }

  const padded: PreparedTrendRow[] = [];
  for (let year = minYear; year <= endYear; year += 1) {
    const iso = `${year}-01-01T00:00:00`;
    const date = parseReportDate(iso);
    const existing = byYear.get(year);

    if (existing) {
      padded.push({
        ...existing,
        report_date: iso,
        tooltipLabel: tooltipLabelFor(date, "Yearly"),
        hasData: true,
      });
      continue;
    }

    padded.push({
      report_date: iso,
      fraud_count: null,
      fraud_rate_pct: null,
      velocity_fraud_share_pct: null,
      tooltipLabel: formatYear(date),
      hasData: false,
    });
  }

  return padded;
}

export function prepareTrendChartData(
  data: TrendRow[],
  granularity: Granularity,
): PreparedTrendRow[] {
  if (!data.length) return [];

  const sorted = [...data].sort(
    (a, b) =>
      parseReportDate(a.report_date).getTime() - parseReportDate(b.report_date).getTime(),
  );

  const rows: PreparedTrendRow[] = sorted.map((row) => {
    const date = parseReportDate(row.report_date);
    return {
      report_date: row.report_date,
      fraud_count: row.fraud_count,
      fraud_rate_pct: row.fraud_rate_pct,
      velocity_fraud_share_pct: row.velocity_fraud_share_pct ?? null,
      is_anomaly: row.is_anomaly,
      tooltipLabel: tooltipLabelFor(date, granularity),
      hasData: true,
    };
  });

  if (granularity === "Yearly") {
    return padYearlyRows(rows);
  }

  return rows;
}

/** For daily data, pin ticks to the first day of each month so labels match monthly style. */
export function getTrendAxisTicks(
  data: PreparedTrendRow[],
  granularity: Granularity,
): string[] | undefined {
  if (granularity !== "Daily") return undefined;

  const ticks: string[] = [];
  let previousMonth = "";

  for (const row of data) {
    const date = parseReportDate(row.report_date);
    const key = monthKey(date);
    if (key !== previousMonth) {
      ticks.push(row.report_date);
      previousMonth = key;
    }
  }

  return ticks;
}

export function createTrendAxisTickFormatter(
  granularity: Granularity,
): (value: string) => string {
  return (value: string) => axisLabelFor(parseReportDate(value), granularity);
}

export function trendTooltipLabel(
  payload: ReadonlyArray<{ payload?: PreparedTrendRow }> | undefined,
): string {
  const row = payload?.[0]?.payload;
  if (!row?.hasData) return "";
  return row.tooltipLabel;
}

export function filterTrendDataByDrill(data: TrendRow[], drill: DateDrilldown): TrendRow[] {
  if (drill.year == null) return data;

  return data.filter((row) => {
    const date = parseReportDate(row.report_date);
    if (drill.month != null) {
      return date.getFullYear() === drill.year && date.getMonth() + 1 === drill.month;
    }
    return date.getFullYear() === drill.year;
  });
}

export function toDateFilter(drill: DateDrilldown): { year?: number; month?: number } | undefined {
  if (drill.year == null) return undefined;
  return {
    year: drill.year,
    month: drill.month ?? undefined,
  };
}

export function effectiveTrendGranularity(
  drill: DateDrilldown,
  manualGranularity: Granularity,
): Granularity {
  if (drill.month != null) return "Daily";
  if (drill.year != null) return "Monthly";
  return manualGranularity;
}

export function canDrillTrend(
  drill: DateDrilldown,
  viewGranularity: Granularity,
): boolean {
  if (drill.month != null) return false;
  if (drill.year != null) return true;
  return viewGranularity === "Yearly" || viewGranularity === "Monthly";
}

export function drillFromTrendPoint(
  drill: DateDrilldown,
  viewGranularity: Granularity,
  reportDate: string,
): DateDrilldown | null {
  const date = parseReportDate(reportDate);

  if (drill.month != null) {
    return null;
  }

  if (drill.year != null) {
    return { year: drill.year, month: date.getMonth() + 1 };
  }

  if (viewGranularity === "Yearly") {
    return { year: date.getFullYear(), month: null };
  }

  if (viewGranularity === "Monthly") {
    return { year: date.getFullYear(), month: date.getMonth() + 1 };
  }

  return null;
}

export function drilldownLabel(drill: DateDrilldown): string | null {
  if (drill.year == null) return null;
  if (drill.month == null) return String(drill.year);
  const date = new Date(drill.year, drill.month - 1, 1);
  return formatMonthYear(date);
}
