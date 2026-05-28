import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Granularity } from "../api/types";
import { DateFilterBar } from "../components/DateFilterBar";
import {
  FraudTrendChart,
  HorizontalBarChart,
  IntervalHistogramChart,
  VelocityBucketsChart,
  VelocityHeatmapChart,
  VelocityScatterChart,
  VelocityShareTrendChart,
  VelocityUsersChart,
  VerticalBarChart,
  formatNumber,
  formatUsd,
} from "../components/charts";
import {
  ChartCard,
  DashboardCanvas,
  EmptyState,
  GranularityToggle,
  KpiCard,
  LoadingGrid,
  MetricColorLegend,
  NotReadyBanner,
  PageHeader,
} from "../components/ui";
import { useDateDrilldown } from "../hooks/useDateDrilldown";
import { canDrillTrend, filterTrendDataByDrill } from "../utils/datetimeAxis";

export function VelocityDeepDivePage() {
  const [manualGranularity, setManualGranularity] = useState<Granularity>("Yearly");
  const {
    drill,
    dateFilter,
    reset,
    setYear,
    applyTrendDrill,
    getTrendGranularity,
  } = useDateDrilldown();

  const trendGranularity = getTrendGranularity(manualGranularity);
  const shareGranularity = getTrendGranularity(manualGranularity);
  const drillable = canDrillTrend(drill, trendGranularity);

  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const enabled = meta.data?.velocity_ready ?? false;
  const filterKey = [drill.year, drill.month];

  const kpis = useQuery({
    queryKey: ["velocity", "kpis", ...filterKey],
    queryFn: () => api.velocity.kpis(dateFilter),
    enabled,
  });
  const buckets = useQuery({
    queryKey: ["velocity", "buckets", ...filterKey],
    queryFn: () => api.velocity.buckets(dateFilter),
    enabled,
  });
  const topUsers = useQuery({
    queryKey: ["velocity", "top-users", ...filterKey],
    queryFn: () => api.velocity.topUsers(dateFilter),
    enabled,
  });
  const countriesCount = useQuery({
    queryKey: ["velocity", "countries-count", ...filterKey],
    queryFn: () => api.velocity.countriesByCount(dateFilter),
    enabled,
  });
  const countriesRate = useQuery({
    queryKey: ["velocity", "countries-rate", ...filterKey],
    queryFn: () => api.velocity.countriesByRate(dateFilter),
    enabled,
  });
  const scatter = useQuery({
    queryKey: ["velocity", "scatter", ...filterKey],
    queryFn: () => api.velocity.scatter(dateFilter),
    enabled,
  });
  const shareTrend = useQuery({
    queryKey: ["velocity", "share-trend", shareGranularity, ...filterKey],
    queryFn: () => api.velocity.shareTrend(shareGranularity, dateFilter),
    enabled,
  });
  const heatmap = useQuery({
    queryKey: ["velocity", "heatmap", ...filterKey],
    queryFn: () => api.velocity.heatmap(dateFilter),
    enabled,
  });
  const intervals = useQuery({
    queryKey: ["velocity", "repeat-interval", ...filterKey],
    queryFn: () => api.velocity.repeatInterval(dateFilter),
    enabled,
  });
  const trends = useQuery({
    queryKey: ["velocity", "trends", trendGranularity, ...filterKey],
    queryFn: () => api.velocity.trends(trendGranularity, dateFilter),
    enabled,
  });

  if (meta.isLoading) return <LoadingGrid />;
  if (!meta.data?.velocity_ready) return <NotReadyBanner />;

  const k = kpis.data;
  const amountTop = [...(topUsers.data ?? [])]
    .sort((a, b) => a.velocity_fraud_amount_usd - b.velocity_fraud_amount_usd)
    .slice(-10);

  const trendSubtitle = drill.month
    ? "Daily view for selected month"
    : drill.year
      ? "Monthly view for selected year — click a month to drill down"
      : "Click a year or month in a trend chart to drill down";

  const shareTrendData = filterTrendDataByDrill(shareTrend.data ?? [], drill);
  const trendData = filterTrendDataByDrill(trends.data ?? [], drill);

  return (
    <DashboardCanvas>
      <PageHeader
        title="Velocity Fraud Deep-Dive"
        description="Who triggers velocity rules, how fast transactions arrive, and whether patterns suggest coordinated attacks."
        actions={<MetricColorLegend />}
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Velocity Fraud Flags" value={formatNumber(k?.velocity_fraud_count)} tone="count" />
        <KpiCard
          label="Velocity Share of Fraud"
          value={`${(k?.velocity_fraud_share_pct ?? 0).toFixed(1)}%`}
          tone="rate"
        />
        <KpiCard
          label="Sum Velocity Fraud Amount"
          value={formatUsd(k?.sum_velocity_fraud_amount_usd)}
          tone="amount"
        />
        <KpiCard
          label="Avg Time Between Flagged Txns"
          value={`${(k?.avg_time_between_flagged_sec ?? 0).toFixed(1)}s`}
          tone="count"
        />
        <KpiCard label="Unique Velocity Users" value={formatNumber(k?.unique_velocity_users)} tone="count" />
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Flagged Transactions by Velocity Bucket">
          {buckets.data?.length ? (
            <VelocityBucketsChart data={buckets.data} />
          ) : (
            <EmptyState message="No velocity fraud in the lookback window." />
          )}
        </ChartCard>
        <ChartCard title="Top Users by Velocity-Flagged Count">
          {topUsers.data?.length ? (
            <VelocityUsersChart data={topUsers.data} />
          ) : (
            <EmptyState message="No velocity fraud users." />
          )}
        </ChartCard>
        <ChartCard title="Top Users by Velocity-Flagged Amount">
          {amountTop.length ? (
            <HorizontalBarChart
              data={amountTop as unknown as Record<string, string | number>[]}
              xKey="velocity_fraud_amount_usd"
              yKey="user_id"
            />
          ) : (
            <EmptyState message="No velocity amount data." />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Top Countries by Velocity Fraud Count">
          {(countriesCount.data?.length ?? 0) > 0 ? (
            <VerticalBarChart
              data={(countriesCount.data ?? []).slice(0, 10) as unknown as Record<string, string | number>[]}
              xKey="country"
              yKey="velocity_fraud_count"
            />
          ) : (
            <EmptyState message="No velocity fraud counts by country." />
          )}
        </ChartCard>
        <ChartCard title="Top Countries by Velocity Fraud Rate" subtitle="≥3 transactions">
          {(countriesRate.data?.length ?? 0) > 0 ? (
            <VerticalBarChart
              data={(countriesRate.data ?? []).slice(0, 10) as unknown as Record<string, string | number>[]}
              xKey="country"
              yKey="velocity_fraud_rate_pct"
            />
          ) : (
            <EmptyState message="No countries with ≥3 txns for velocity rate ranking." />
          )}
        </ChartCard>
        <ChartCard
          title="Amount vs Velocity Scatter"
          subtitle="0–2s window, log-scaled velocity, colored by country"
        >
          {scatter.data?.length ? (
            <VelocityScatterChart data={scatter.data} />
          ) : (
            <EmptyState message="No velocity scatter data (need consecutive txns per user)." />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard
          title="Velocity Share of Total Fraud"
          actions={
            drill.year == null ? (
              <GranularityToggle value={manualGranularity} onChange={setManualGranularity} />
            ) : null
          }
        >
          {shareTrendData.length ? (
            <VelocityShareTrendChart
              data={shareTrendData}
              granularity={shareGranularity}
              drillable={drillable}
              onDrill={(reportDate) => applyTrendDrill(reportDate, shareGranularity)}
            />
          ) : (
            <EmptyState message="No velocity share trend data." />
          )}
        </ChartCard>
        <ChartCard title="Velocity Flags by Hour × Day">
          {heatmap.data?.length ? (
            <VelocityHeatmapChart data={heatmap.data} />
          ) : (
            <EmptyState message="No velocity heatmap data." />
          )}
        </ChartCard>
        <ChartCard title="Time Between Consecutive Velocity Flags">
          {intervals.data?.length ? (
            <IntervalHistogramChart data={intervals.data} />
          ) : (
            <EmptyState message="No repeat interval data." />
          )}
        </ChartCard>
      </div>

      <ChartCard
        title="Velocity-Flagged Transactions Over Time"
        subtitle={trendSubtitle}
        actions={
          drill.year == null ? (
            <GranularityToggle value={manualGranularity} onChange={setManualGranularity} />
          ) : null
        }
      >
        <DateFilterBar drill={drill} onReset={reset} onSelectYear={setYear} />
        {trendData.length ? (
          <FraudTrendChart
            data={trendData}
            granularity={trendGranularity}
            drillable={drillable}
            onDrill={(reportDate) => applyTrendDrill(reportDate, trendGranularity)}
          />
        ) : (
          <EmptyState message="No velocity trend data yet." />
        )}
      </ChartCard>
    </DashboardCanvas>
  );
}
