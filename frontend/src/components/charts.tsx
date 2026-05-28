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
import { Fragment, useMemo } from "react";
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
import { chartTooltipProps } from "../utils/chartTooltip";
import { heatmapIntensity, ylOrRdColor, ylOrRdGradient } from "../utils/heatmapColors";
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
        <Tooltip {...tooltipStyle} {...chartTooltipProps} />
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
  const sortedData = useMemo(
    () => [...data].sort((a, b) => Number(b[xKey]) - Number(a[xKey])),
    [data, xKey],
  );

  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart
        data={sortedData}
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
        <Tooltip {...tooltipStyle} {...chartTooltipProps} />
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
        <Tooltip {...tooltipStyle} {...chartTooltipProps} />
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
        <Tooltip
          {...tooltipStyle}
          {...chartTooltipProps}
          labelFormatter={(_, payload) => trendTooltipLabel(payload)}
        />
        <Legend />
        <Bar
          yAxisId="left"
          dataKey="fraud_count"
          name="Fraud Count"
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
          name="Fraud Rate"
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
        <Tooltip
          {...tooltipStyle}
          {...chartTooltipProps}
          cursor={{ strokeDasharray: "3 3" }}
          labelFormatter={(_, payload) => {
            const row = payload?.[0]?.payload as VelocityScatterRow | undefined;
            return row?.user_id ?? "";
          }}
        />
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
        <Tooltip
          {...tooltipStyle}
          {...chartTooltipProps}
          labelFormatter={(_, payload) => trendTooltipLabel(payload)}
        />
        <Line
          type="monotone"
          dataKey="velocity_fraud_share_pct"
          name="Velocity Fraud Share"
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

function HeatmapCell({
  dayLabel,
  hour,
  value,
  max,
}: {
  dayLabel: string;
  hour: number;
  value: number;
  max: number;
}) {
  return (
    <div className="group relative min-h-0 min-w-0">
      <div
        className="h-full min-h-[0.875rem] w-full rounded-[2px] border border-slate-800/30"
        style={{ backgroundColor: ylOrRdColor(heatmapIntensity(value, max)) }}
        aria-label={`${dayLabel} ${hour}:00, ${value.toLocaleString()} velocity flags`}
      />
      <div
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-[calc(100%+4px)] z-50 hidden -translate-x-1/2 group-hover:block"
      >
        <div className="whitespace-nowrap rounded-lg border border-surface-border bg-slate-900/95 px-2.5 py-1.5 text-[10px] shadow-xl">
          <p className="font-medium text-white">
            {dayLabel} · {hour}:00
          </p>
          <p className="mt-0.5 text-slate-300">
            {value.toLocaleString()} velocity flags
          </p>
        </div>
      </div>
    </div>
  );
}

export function VelocityHeatmapChart({ data }: { data: HeatmapRow[] }) {
  const hours = useMemo(() => Array.from({ length: 24 }, (_, hour) => hour), []);

  const { cells, max } = useMemo(() => {
    const lookup = new Map<string, number>();
    let peak = 0;

    for (const row of data) {
      lookup.set(`${row.day_of_week}-${row.hour_of_day}`, row.velocity_fraud_count);
      peak = Math.max(peak, row.velocity_fraud_count);
    }

    const grid = DAY_LABELS.map((dayLabel, dayIdx) =>
      hours.map((hour) => {
        const value = lookup.get(`${dayIdx}-${hour}`) ?? 0;
        return { dayLabel, hour, value };
      }),
    );

    return { cells: grid, max: Math.max(1, peak) };
  }, [data, hours]);

  return (
    <div className="flex w-full flex-col gap-2 overflow-visible">
      <div
        className="grid w-full gap-px overflow-visible"
        style={{
          gridTemplateColumns: "1.5rem repeat(24, minmax(0, 1fr))",
          gridTemplateRows: "auto repeat(7, minmax(0, 1fr))",
          height: "11rem",
        }}
      >
        <div />
        {hours.map((hour) => (
          <div
            key={`h-${hour}`}
            className="flex items-end justify-center pb-0.5 text-[8px] leading-none text-slate-500"
          >
            {hour % 2 === 0 ? hour : ""}
          </div>
        ))}

        {cells.map((row) => (
          <Fragment key={row[0].dayLabel}>
            <div className="flex items-center text-[10px] font-medium leading-none text-slate-400">
              {row[0].dayLabel}
            </div>
            {row.map(({ dayLabel, hour, value }) => (
              <HeatmapCell
                key={`${dayLabel}-${hour}`}
                dayLabel={dayLabel}
                hour={hour}
                value={value}
                max={max}
              />
            ))}
          </Fragment>
        ))}
      </div>

      <div className="w-full pl-6">
        <div className="mb-1 flex justify-between text-[10px] text-slate-500">
          <span>0</span>
          <span className="text-slate-400">Velocity flags</span>
          <span>{max.toLocaleString()}</span>
        </div>
        <div
          className="h-2 w-full rounded-sm border border-slate-800/40"
          style={{ background: ylOrRdGradient("to right") }}
        />
      </div>
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
