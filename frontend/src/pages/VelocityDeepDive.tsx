import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Granularity } from "../api/types";
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
  NotReadyBanner,
  PageHeader,
} from "../components/ui";

export function VelocityDeepDivePage() {
  const [trendGranularity, setTrendGranularity] = useState<Granularity>("Daily");
  const [shareGranularity, setShareGranularity] = useState<Granularity>("Daily");

  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const enabled = meta.data?.velocity_ready ?? false;

  const kpis = useQuery({ queryKey: ["velocity", "kpis"], queryFn: api.velocity.kpis, enabled });
  const buckets = useQuery({ queryKey: ["velocity", "buckets"], queryFn: api.velocity.buckets, enabled });
  const topUsers = useQuery({ queryKey: ["velocity", "top-users"], queryFn: api.velocity.topUsers, enabled });
  const countriesCount = useQuery({ queryKey: ["velocity", "countries-count"], queryFn: api.velocity.countriesByCount, enabled });
  const countriesRate = useQuery({ queryKey: ["velocity", "countries-rate"], queryFn: api.velocity.countriesByRate, enabled });
  const scatter = useQuery({ queryKey: ["velocity", "scatter"], queryFn: api.velocity.scatter, enabled });
  const shareTrend = useQuery({
    queryKey: ["velocity", "share-trend", shareGranularity],
    queryFn: () => api.velocity.shareTrend(shareGranularity),
    enabled,
  });
  const heatmap = useQuery({ queryKey: ["velocity", "heatmap"], queryFn: api.velocity.heatmap, enabled });
  const intervals = useQuery({ queryKey: ["velocity", "repeat-interval"], queryFn: api.velocity.repeatInterval, enabled });
  const trends = useQuery({
    queryKey: ["velocity", "trends", trendGranularity],
    queryFn: () => api.velocity.trends(trendGranularity),
    enabled,
  });

  if (meta.isLoading) return <LoadingGrid />;
  if (!meta.data?.velocity_ready) return <NotReadyBanner />;

  const k = kpis.data;
  const amountTop = [...(topUsers.data ?? [])]
    .sort((a, b) => a.velocity_fraud_amount_usd - b.velocity_fraud_amount_usd)
    .slice(-10);

  return (
    <DashboardCanvas>
      <PageHeader
        title="Velocity Fraud Deep-Dive"
        description="Who triggers velocity rules, how fast transactions arrive, and whether patterns suggest coordinated attacks."
      />

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <KpiCard label="Velocity Fraud Flags" value={formatNumber(k?.velocity_fraud_count)} tone="danger" />
        <KpiCard label="Velocity Share of Fraud" value={`${(k?.velocity_fraud_share_pct ?? 0).toFixed(1)}%`} tone="warning" />
        <KpiCard label="Sum Velocity Fraud Amount" value={formatUsd(k?.sum_velocity_fraud_amount_usd)} tone="danger" />
        <KpiCard
          label="Avg Time Between Flagged Txns"
          value={`${(k?.avg_time_between_flagged_sec ?? 0).toFixed(1)}s`}
        />
        <KpiCard label="Unique Velocity Users" value={formatNumber(k?.unique_velocity_users)} />
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
              color="#f59e0b"
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
              color="#a855f7"
            />
          ) : (
            <EmptyState message="No countries with ≥3 txns for velocity rate ranking." />
          )}
        </ChartCard>
        <ChartCard title="Amount vs Velocity Scatter" subtitle="Transactions within 5 seconds apart">
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
          actions={<GranularityToggle value={shareGranularity} onChange={setShareGranularity} />}
        >
          {shareTrend.data?.length ? (
            <VelocityShareTrendChart data={shareTrend.data} />
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
        subtitle="Volume bars with velocity fraud rate overlay"
        actions={<GranularityToggle value={trendGranularity} onChange={setTrendGranularity} />}
      >
        {trends.data?.length ? (
          <FraudTrendChart data={trends.data} />
        ) : (
          <EmptyState message="No velocity trend data yet." />
        )}
      </ChartCard>
    </DashboardCanvas>
  );
}
