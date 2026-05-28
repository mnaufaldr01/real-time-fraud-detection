import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import { useMemo } from "react";
import type {
  CountryRow,
  CurrencyRow,
  FlagReasonRow,
  Granularity,
  HeatmapRow,
  IntervalRow,
  MerchantRow,
  TopUserRow,
  TrendRow,
  VelocityBucketRow,
  VelocityScatterRow,
  VelocityUserRow,
} from "../api/types";
import {
  createTrendAxisTickFormatter,
  getTrendAxisTicks,
  prepareTrendChartData,
  type PreparedTrendRow,
  trendTooltipLabel,
} from "../utils/datetimeAxis";

const COLORS = {
  legit: "#22c55e",
  flagged: "#ef4444",
  accent: "#06b6d4",
  purple: "#a855f7",
  warning: "#f59e0b",
  grid: "#334155",
};

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export const CHART_HEIGHT = 210;
export const TREND_HEIGHT = 240;

const tooltipStyle = {
  contentStyle: {
    background: "rgba(15, 23, 42, 0.95)",
    border: "1px solid #334155",
    borderRadius: "0.75rem",
  },
};

function trendPointFromClick(entry: unknown): PreparedTrendRow | undefined {
  if (!entry || typeof entry !== "object") return undefined;
  if ("payload" in entry) {
    return (entry as { payload?: PreparedTrendRow }).payload;
  }
  return entry as PreparedTrendRow;
}

export function CurrencyStackedChart({ data }: { data: CurrencyRow[] }) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis dataKey="currency" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <Tooltip {...tooltipStyle} />
        <Legend />
        <Bar dataKey="legitimate_count" name="Legitimate" stackId="a" fill={COLORS.legit} />
        <Bar dataKey="flagged_count" name="Flagged" stackId="a" fill={COLORS.flagged} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function HorizontalBarChart({
  data,
  xKey,
  yKey,
  color = COLORS.accent,
}: {
  data: Record<string, string | number>[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 8, right: 24, left: 8, bottom: 0 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} horizontal={false} />
        <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis
          type="category"
          dataKey={yKey}
          width={90}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
        />
        <Tooltip {...tooltipStyle} />
        <Bar dataKey={xKey} fill={color} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VerticalBarChart({
  data,
  xKey,
  yKey,
  color = COLORS.flagged,
}: {
  data: Record<string, string | number>[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis dataKey={xKey} tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <Tooltip {...tooltipStyle} />
        <Bar dataKey={yKey} fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function FraudTrendChart({
  data,
  granularity,
  onDrill,
  drillable = false,
}: {
  data: TrendRow[];
  granularity: Granularity;
  onDrill?: (reportDate: string) => void;
  drillable?: boolean;
}) {
  const chartData = useMemo(
    () => prepareTrendChartData(data, granularity),
    [data, granularity],
  );
  const tickFormatter = useMemo(
    () => createTrendAxisTickFormatter(granularity),
    [granularity],
  );
  const axisTicks = useMemo(
    () => getTrendAxisTicks(chartData, granularity),
    [chartData, granularity],
  );

  const handlePointClick = (row: PreparedTrendRow | undefined) => {
    if (!row?.hasData || !onDrill) return;
    onDrill(row.report_date);
  };

  return (
    <ResponsiveContainer width="100%" height={TREND_HEIGHT}>
      <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis
          dataKey="report_date"
          ticks={axisTicks}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={tickFormatter}
          interval={axisTicks ? 0 : "preserveStartEnd"}
          minTickGap={axisTicks ? 0 : 12}
        />
        <YAxis
          yAxisId="left"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          label={{ value: "Count", angle: -90, position: "insideLeft", fill: "#64748b" }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          label={{ value: "Rate %", angle: 90, position: "insideRight", fill: "#64748b" }}
        />
        <Tooltip {...tooltipStyle} labelFormatter={(_, payload) => trendTooltipLabel(payload)} />
        <Legend />
        <Bar
          yAxisId="left"
          dataKey="fraud_count"
          name="Fraud count"
          fill={COLORS.flagged}
          opacity={0.75}
          cursor={drillable ? "pointer" : undefined}
          onClick={
            drillable
              ? (entry) => handlePointClick(trendPointFromClick(entry))
              : undefined
          }
        />
        <Line
          yAxisId="right"
          type="monotone"
          dataKey="fraud_rate_pct"
          name="Fraud rate %"
          stroke={COLORS.accent}
          strokeWidth={2}
          dot={drillable ? { r: 3, cursor: "pointer" } : false}
          connectNulls={false}
          activeDot={drillable ? { r: 5, cursor: "pointer" } : undefined}
          onClick={
            drillable
              ? (entry) => handlePointClick(trendPointFromClick(entry))
              : undefined
          }
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function FlagReasonsChart({ data }: { data: FlagReasonRow[] }) {
  const sorted = [...data].sort((a, b) => a.reason_count - b.reason_count);
  return (
    <HorizontalBarChart
      data={sorted as unknown as Record<string, string | number>[]}
      xKey="reason_count"
      yKey="reason"
      color={COLORS.purple}
    />
  );
}

export function TopUsersCharts({ data }: { data: TopUserRow[] }) {
  const byCount = [...data].sort((a, b) => a.fraud_count - b.fraud_count).slice(-10);
  const byAmount = [...data]
    .sort((a, b) => a.fraud_amount_usd - b.fraud_amount_usd)
    .slice(-10);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <HorizontalBarChart
        data={byCount as unknown as Record<string, string | number>[]}
        xKey="fraud_count"
        yKey="user_id"
      />
      <HorizontalBarChart
        data={byAmount as unknown as Record<string, string | number>[]}
        xKey="fraud_amount_usd"
        yKey="user_id"
        color={COLORS.warning}
      />
    </div>
  );
}

export function MerchantCharts({
  byCount,
  byRate,
}: {
  byCount: MerchantRow[];
  byRate: MerchantRow[];
}) {
  const countTop = [...byCount].sort((a, b) => a.fraud_count - b.fraud_count).slice(-10);
  const amountTop = [...byCount]
    .sort((a, b) => (a.fraud_amount_usd ?? 0) - (b.fraud_amount_usd ?? 0))
    .slice(-10);
  const rateTop = [...byRate].sort((a, b) => a.fraud_rate_pct! - b.fraud_rate_pct!).slice(-10);

  return (
    <div className="grid gap-4 xl:grid-cols-3">
      <HorizontalBarChart
        data={countTop as unknown as Record<string, string | number>[]}
        xKey="fraud_count"
        yKey="merchant_id"
      />
      <HorizontalBarChart
        data={amountTop as unknown as Record<string, string | number>[]}
        xKey="fraud_amount_usd"
        yKey="merchant_id"
        color={COLORS.warning}
      />
      <HorizontalBarChart
        data={rateTop as unknown as Record<string, string | number>[]}
        xKey="fraud_rate_pct"
        yKey="merchant_id"
        color={COLORS.purple}
      />
    </div>
  );
}

export function CountryCharts({
  byCount,
  byRate,
  countKey = "fraud_count",
  rateKey = "fraud_rate_pct",
}: {
  byCount: CountryRow[];
  byRate: CountryRow[];
  countKey?: keyof CountryRow;
  rateKey?: keyof CountryRow;
}) {
  const countTop = [...byCount].slice(0, 10);
  const rateTop = [...byRate].slice(0, 10);

  return (
    <div className="grid gap-4 xl:grid-cols-2">
      <VerticalBarChart
        data={countTop as unknown as Record<string, string | number>[]}
        xKey="country"
        yKey={countKey as string}
      />
      <VerticalBarChart
        data={rateTop as unknown as Record<string, string | number>[]}
        xKey="country"
        yKey={rateKey as string}
        color={COLORS.purple}
      />
    </div>
  );
}

export function VelocityScatterChart({ data }: { data: VelocityScatterRow[] }) {
  const filtered = data.filter((row) => row.velocity_seconds <= 5);
  return (
    <ResponsiveContainer width="100%" height={TREND_HEIGHT}>
      <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis
          type="number"
          dataKey="velocity_seconds"
          name="Velocity"
          domain={[0, 5]}
          tick={{ fill: "#94a3b8", fontSize: 12 }}
          label={{ value: "Seconds between txns", position: "insideBottom", offset: -2, fill: "#64748b" }}
        />
        <YAxis
          type="number"
          dataKey="amount_usd"
          name="Amount USD"
          tick={{ fill: "#94a3b8", fontSize: 12 }}
        />
        <ZAxis range={[60, 60]} />
        <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: "3 3" }} />
        <Scatter data={filtered} fill={COLORS.accent} fillOpacity={0.75} />
      </ScatterChart>
    </ResponsiveContainer>
  );
}

export function VelocityShareTrendChart({
  data,
  granularity,
  onDrill,
  drillable = false,
}: {
  data: TrendRow[];
  granularity: Granularity;
  onDrill?: (reportDate: string) => void;
  drillable?: boolean;
}) {
  const chartData = useMemo(
    () => prepareTrendChartData(data, granularity),
    [data, granularity],
  );
  const tickFormatter = useMemo(
    () => createTrendAxisTickFormatter(granularity),
    [granularity],
  );
  const axisTicks = useMemo(
    () => getTrendAxisTicks(chartData, granularity),
    [chartData, granularity],
  );

  const handlePointClick = (row: PreparedTrendRow | undefined) => {
    if (!row?.hasData || !onDrill) return;
    onDrill(row.report_date);
  };

  return (
    <ResponsiveContainer width="100%" height={TREND_HEIGHT}>
      <ComposedChart data={chartData}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis
          dataKey="report_date"
          ticks={axisTicks}
          tick={{ fill: "#94a3b8", fontSize: 11 }}
          tickFormatter={tickFormatter}
          interval={axisTicks ? 0 : "preserveStartEnd"}
          minTickGap={axisTicks ? 0 : 12}
        />
        <YAxis tick={{ fill: "#94a3b8", fontSize: 12 }} />
        <Tooltip {...tooltipStyle} labelFormatter={(_, payload) => trendTooltipLabel(payload)} />
        <Line
          type="monotone"
          dataKey="velocity_fraud_share_pct"
          name="Velocity share %"
          stroke={COLORS.purple}
          strokeWidth={2}
          dot={drillable ? { r: 3, cursor: "pointer" } : false}
          connectNulls={false}
          onClick={
            drillable
              ? (entry) => handlePointClick(trendPointFromClick(entry))
              : undefined
          }
        />
      </ComposedChart>
    </ResponsiveContainer>
  );
}

export function VelocityHeatmapChart({ data }: { data: HeatmapRow[] }) {
  const matrix: Record<string, Record<string, number>> = {};
  for (const row of data) {
    const day = DAY_LABELS[row.day_of_week] ?? String(row.day_of_week);
    matrix[day] ??= {};
    matrix[day][String(row.hour_of_day)] = row.velocity_fraud_count;
  }

  const hours = Array.from({ length: 24 }, (_, hour) => String(hour));
  const rows = DAY_LABELS.map((day) => {
    const entry: Record<string, string | number> = { day };
    for (const hour of hours) {
      entry[hour] = matrix[day]?.[hour] ?? 0;
    }
    return entry;
  });

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[520px] border-collapse text-[10px]">
        <thead>
          <tr>
            <th className="p-1 text-left text-slate-500">Day</th>
            {hours.map((hour) => (
              <th key={hour} className="p-0.5 text-center font-normal text-slate-500">
                {hour}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={String(row.day)}>
              <td className="p-1 font-medium text-slate-300">{row.day}</td>
              {hours.map((hour) => {
                const value = Number(row[hour] ?? 0);
                const intensity = Math.min(value / 10, 1);
                return (
                  <td key={hour} className="p-0.5">
                    <div
                      className="flex h-5 items-center justify-center rounded text-[9px] text-slate-200"
                      style={{
                        backgroundColor: `rgba(239, 68, 68, ${0.12 + intensity * 0.75})`,
                      }}
                      title={`${value} flags`}
                    >
                      {value > 0 ? value : ""}
                    </div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function IntervalHistogramChart({ data }: { data: IntervalRow[] }) {
  return (
    <VerticalBarChart
      data={data as unknown as Record<string, string | number>[]}
      xKey="interval_bucket"
      yKey="interval_count"
      color={COLORS.purple}
    />
  );
}

export function VelocityUsersChart({ data }: { data: VelocityUserRow[] }) {
  const top = [...data]
    .sort((a, b) => a.velocity_fraud_count - b.velocity_fraud_count)
    .slice(-10);
  return (
    <HorizontalBarChart
      data={top as unknown as Record<string, string | number>[]}
      xKey="velocity_fraud_count"
      yKey="user_id"
    />
  );
}

export function VelocityBucketsChart({ data }: { data: VelocityBucketRow[] }) {
  return (
    <VerticalBarChart
      data={data as unknown as Record<string, string | number>[]}
      xKey="velocity_bucket"
      yKey="fraud_count"
    />
  );
}

export const formatUsd = (value?: number) =>
  value == null ? "$0.00" : `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const formatPct = (value?: number) =>
  value == null ? "0.00%" : `${value.toFixed(2)}%`;

export const formatNumber = (value?: number) =>
  value == null ? "0" : value.toLocaleString();
