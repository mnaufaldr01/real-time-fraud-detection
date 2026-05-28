import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Customized,
  Legend,
  Line,
  ReferenceLine,
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
import { chartTooltipProps, formatTooltipAmount } from "../utils/chartTooltip";
import { heatmapIntensity, ylOrRdColor, ylOrRdGradient } from "../utils/heatmapColors";
import { CHART_PALETTE, METRIC_COLORS, SCATTER_COUNTRY_COLORS, colorForMetricKey } from "../theme/palette";
import {
  createTrendAxisTickFormatter,
  getTrendAxisTicks,
  prepareTrendChartData,
  type PreparedTrendRow,
  trendTooltipLabel,
} from "../utils/datetimeAxis";

const COLORS = {
  legit: CHART_PALETTE.legit,
  flagged: METRIC_COLORS.count,
  count: METRIC_COLORS.count,
  amount: METRIC_COLORS.amount,
  rate: METRIC_COLORS.rate,
  grid: CHART_PALETTE.grid,
};

const AXIS = {
  tick: { fill: CHART_PALETTE.text, fontSize: 12 },
  tickSm: { fill: CHART_PALETTE.text, fontSize: 11 },
  label: { fill: CHART_PALETTE.textMuted, fontSize: 11 },
};

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const SCATTER_LOG_EPS = 0.01;
const SCATTER_MAX_VELOCITY_SEC = 2;
const SCATTER_DOT_SIZE = 10;
const SCATTER_OPACITY = 0.22;
const SCATTER_LOG_TICKS_SEC = [0.01, 0.05, 0.1, 0.25, 0.5, 1, 2];
const SCATTER_COUNTRY_PALETTE = SCATTER_COUNTRY_COLORS;

type PlottedScatterRow = VelocityScatterRow & { log_velocity: number };

function toLogVelocity(seconds: number): number {
  return Math.log10(seconds + SCATTER_LOG_EPS);
}

function fromLogVelocity(logValue: number): number {
  return Math.max(0, Math.pow(10, logValue) - SCATTER_LOG_EPS);
}

function scatterQuantile(sorted: number[], q: number): number {
  if (!sorted.length) return 0;
  const idx = Math.min(sorted.length - 1, Math.floor(sorted.length * q));
  return sorted[idx] ?? 0;
}

function scatterMedian(values: number[]): number {
  if (!values.length) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0
    ? ((sorted[mid - 1] ?? 0) + (sorted[mid] ?? 0)) / 2
    : (sorted[mid] ?? 0);
}

function ScatterPriorityLabel({
  x,
  y,
  xAxisMap,
  yAxisMap,
  offset,
}: {
  x: number;
  y: number;
  xAxisMap?: Record<string, { scale: (value: number) => number }>;
  yAxisMap?: Record<string, { scale: (value: number) => number }>;
  offset?: { left?: number; top?: number };
}) {
  const xAxis = xAxisMap ? Object.values(xAxisMap)[0] : undefined;
  const yAxis = yAxisMap ? Object.values(yAxisMap)[0] : undefined;
  if (!xAxis?.scale || !yAxis?.scale) return null;

  const cx = (offset?.left ?? 0) + xAxis.scale(x);
  const cy = (offset?.top ?? 0) + yAxis.scale(y);

  return (
    <g>
      <rect
        x={cx - 76}
        y={cy - 24}
        width={152}
        height={18}
        rx={4}
        fill="rgba(255, 255, 255, 0.92)"
      />
      <text
        x={cx}
        y={cy - 11}
        textAnchor="middle"
        fill={CHART_PALETTE.amberDark}
        fontSize={11}
        fontWeight={700}
      >
        Priority Investigation
      </text>
    </g>
  );
}

export const CHART_HEIGHT = 210;
export const TREND_HEIGHT = 240;

const tooltipStyle = {
  contentStyle: {
    background: "#FFFFFF",
    border: "1px solid #E0E0E0",
    borderRadius: "6px",
    color: CHART_PALETTE.text,
  },
  itemStyle: { color: CHART_PALETTE.text },
  labelStyle: { color: CHART_PALETTE.text, fontWeight: 700 },
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
        <XAxis dataKey="currency" tick={AXIS.tick} />
        <YAxis tick={AXIS.tick} />
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
  color,
}: {
  data: Record<string, string | number>[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  const barColor = color ?? colorForMetricKey(xKey);
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
        <XAxis type="number" tick={AXIS.tick} />
        <YAxis
          type="category"
          dataKey={yKey}
          width={90}
          tick={AXIS.tickSm}
        />
        <Tooltip {...tooltipStyle} {...chartTooltipProps} />
        <Bar dataKey={xKey} fill={barColor} radius={[0, 4, 4, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function VerticalBarChart({
  data,
  xKey,
  yKey,
  color,
}: {
  data: Record<string, string | number>[];
  xKey: string;
  yKey: string;
  color?: string;
}) {
  const barColor = color ?? colorForMetricKey(yKey);
  return (
    <ResponsiveContainer width="100%" height={CHART_HEIGHT}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis dataKey={xKey} tick={AXIS.tick} />
        <YAxis tick={AXIS.tick} />
        <Tooltip {...tooltipStyle} {...chartTooltipProps} />
        <Bar dataKey={yKey} fill={barColor} radius={[4, 4, 0, 0]} />
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
          tick={AXIS.tickSm}
          tickFormatter={tickFormatter}
          interval={axisTicks ? 0 : "preserveStartEnd"}
          minTickGap={axisTicks ? 0 : 12}
        />
        <YAxis
          yAxisId="left"
          tick={AXIS.tick}
          label={{ value: "Count", angle: -90, position: "insideLeft", fill: CHART_PALETTE.textMuted }}
        />
        <YAxis
          yAxisId="right"
          orientation="right"
          tick={AXIS.tick}
          label={{ value: "Rate %", angle: 90, position: "insideRight", fill: CHART_PALETTE.textMuted }}
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
          fill={COLORS.count}
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
          stroke={COLORS.rate}
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
      />
      <HorizontalBarChart
        data={rateTop as unknown as Record<string, string | number>[]}
        xKey="fraud_rate_pct"
        yKey="merchant_id"
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
      />
    </div>
  );
}

export function VelocityScatterChart({ data }: { data: VelocityScatterRow[] }) {
  const {
    plotted,
    countryColors,
    legendItems,
    xMedian,
    yMedian,
    annotX,
    annotY,
    xDomain,
    xTicks,
  } = useMemo(() => {
    const filtered = data.filter(
      (row) => row.velocity_seconds >= 0 && row.velocity_seconds <= SCATTER_MAX_VELOCITY_SEC,
    );

    const velocities = filtered.map((row) => row.velocity_seconds);
    const amounts = filtered.map((row) => row.amount_usd);
    const sortedVelocities = [...velocities].sort((a, b) => a - b);
    const sortedAmounts = [...amounts].sort((a, b) => a - b);

    const xMed = scatterMedian(velocities);
    const yMed = scatterMedian(amounts);
    const xQ15 = Math.min(
      scatterQuantile(sortedVelocities, 0.15),
      SCATTER_MAX_VELOCITY_SEC - 0.05,
    );
    const yQ85 = scatterQuantile(sortedAmounts, 0.85);

    const countryCounts = new Map<string, number>();
    for (const row of filtered) {
      countryCounts.set(row.country, (countryCounts.get(row.country) ?? 0) + 1);
    }

    const countries = [...countryCounts.keys()].sort((a, b) => {
      const diff = (countryCounts.get(b) ?? 0) - (countryCounts.get(a) ?? 0);
      return diff !== 0 ? diff : a.localeCompare(b);
    });

    const colors = Object.fromEntries(
      countries.map((country, index) => [
        country,
        SCATTER_COUNTRY_PALETTE[index % SCATTER_COUNTRY_PALETTE.length],
      ]),
    );

    const legendCountries = countries.slice(0, 8);

    return {
      plotted: filtered.map((row) => ({
        ...row,
        log_velocity: toLogVelocity(row.velocity_seconds),
      })),
      countryColors: colors,
      legendItems: legendCountries.map((country) => ({
        value: country,
        type: "circle" as const,
        color: colors[country],
      })),
      xMedian: toLogVelocity(xMed),
      yMedian: yMed,
      annotX: toLogVelocity(xQ15),
      annotY: yQ85,
      xDomain: [
        toLogVelocity(0),
        toLogVelocity(SCATTER_MAX_VELOCITY_SEC),
      ] as [number, number],
      xTicks: SCATTER_LOG_TICKS_SEC.map(toLogVelocity),
    };
  }, [data]);

  if (!plotted.length) {
    return (
      <ResponsiveContainer width="100%" height={TREND_HEIGHT}>
        <ScatterChart margin={{ top: 8, right: 16, left: 8, bottom: 24 }} />
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={TREND_HEIGHT}>
      <ScatterChart margin={{ top: 16, right: 16, left: 8, bottom: 24 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={COLORS.grid} />
        <XAxis
          type="number"
          dataKey="log_velocity"
          name="Velocity"
          domain={xDomain}
          ticks={xTicks}
          tick={AXIS.tickSm}
          tickFormatter={(logValue) => {
            const seconds = fromLogVelocity(Number(logValue));
            if (seconds < 0.1) return `${seconds.toFixed(2)}s`;
            if (seconds < 1) return `${seconds.toFixed(2)}s`;
            return `${seconds.toFixed(1)}s`;
          }}
          label={{
            value: "Seconds between txns (log scale, 0–2s)",
            position: "insideBottom",
            offset: -4,
            fill: CHART_PALETTE.textMuted,
            fontSize: 11,
          }}
        />
        <YAxis
          type="number"
          dataKey="amount_usd"
          name="Amount USD"
          tick={AXIS.tick}
          tickFormatter={(value) => formatTooltipAmount(Number(value))}
        />
        <ZAxis range={[SCATTER_DOT_SIZE, SCATTER_DOT_SIZE]} />
        <Tooltip
          {...tooltipStyle}
          cursor={{ strokeDasharray: "3 3" }}
          labelFormatter={(_, payload) => {
            const row = payload?.[0]?.payload as PlottedScatterRow | undefined;
            if (!row) return "";
            return `${row.user_id} · ${row.country}`;
          }}
          formatter={(value, name, item) => {
            const row = item?.payload as PlottedScatterRow | undefined;
            const key = String(item?.dataKey ?? name ?? "");
            if (key === "log_velocity" && row) {
              return [`${row.velocity_seconds.toFixed(3)}s`, "Velocity"];
            }
            if (key === "amount_usd") {
              return [formatTooltipAmount(Number(value)), "Amount"];
            }
            return [String(value ?? ""), String(name ?? "")];
          }}
        />
        <Legend
          content={() => (
            <ul className="flex flex-wrap justify-center gap-x-3 gap-y-1 pt-2 text-[11px]">
              {legendItems.map((item) => (
                <li key={item.value} className="flex items-center gap-1.5 text-ink-muted">
                  <span
                    className="inline-block h-2 w-2 rounded-full"
                    style={{ backgroundColor: item.color }}
                  />
                  {item.value}
                </li>
              ))}
            </ul>
          )}
        />
        <ReferenceLine
          x={xMedian}
          stroke="#95a5a6"
          strokeDasharray="4 4"
          strokeOpacity={0.6}
        />
        <ReferenceLine
          y={yMedian}
          stroke="#95a5a6"
          strokeDasharray="4 4"
          strokeOpacity={0.6}
        />
        <Customized
          component={(props: {
            xAxisMap?: Record<string, { scale: (value: number) => number }>;
            yAxisMap?: Record<string, { scale: (value: number) => number }>;
            offset?: { left?: number; top?: number };
          }) => (
            <ScatterPriorityLabel {...props} x={annotX} y={annotY} />
          )}
        />
        <Scatter data={plotted} fill={COLORS.amount} fillOpacity={SCATTER_OPACITY}>
          {plotted.map((row) => (
            <Cell
              key={row.transaction_id}
              fill={countryColors[row.country] ?? COLORS.amount}
            />
          ))}
        </Scatter>
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
          tick={AXIS.tickSm}
          tickFormatter={tickFormatter}
          interval={axisTicks ? 0 : "preserveStartEnd"}
          minTickGap={axisTicks ? 0 : 12}
        />
        <YAxis tick={AXIS.tick} />
        <Tooltip
          {...tooltipStyle}
          {...chartTooltipProps}
          labelFormatter={(_, payload) => trendTooltipLabel(payload)}
        />
        <Line
          type="monotone"
          dataKey="velocity_fraud_share_pct"
          name="Velocity Fraud Share"
          stroke={COLORS.rate}
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
        className="h-full min-h-[0.875rem] w-full rounded-[2px] border border-surface-border/80"
        style={{ backgroundColor: ylOrRdColor(heatmapIntensity(value, max)) }}
        aria-label={`${dayLabel} ${hour}:00, ${value.toLocaleString()} velocity flags`}
      />
      <div
        role="tooltip"
        className="pointer-events-none absolute left-1/2 top-[calc(100%+4px)] z-50 hidden -translate-x-1/2 group-hover:block"
      >
        <div className="whitespace-nowrap rounded-card border border-surface-border bg-white px-2.5 py-1.5 text-[10px] shadow-card">
          <p className="font-medium text-ink">
            {dayLabel} · {hour}:00
          </p>
          <p className="mt-0.5 text-ink-mid">
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
            className="flex items-end justify-center pb-0.5 text-[8px] leading-none text-ink-muted"
          >
            {hour % 2 === 0 ? hour : ""}
          </div>
        ))}

        {cells.map((row) => (
          <Fragment key={row[0].dayLabel}>
            <div className="flex items-center text-[10px] font-medium leading-none text-ink-mid">
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
        <div className="mb-1 flex justify-between text-[10px] text-ink-muted">
          <span>0</span>
          <span className="text-ink-mid">Velocity flags</span>
          <span>{max.toLocaleString()}</span>
        </div>
        <div
          className="h-2 w-full rounded-sm border border-surface-border/80"
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
