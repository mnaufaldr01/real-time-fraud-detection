import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api";
import type { Granularity } from "../api/types";
import { DateFilterBar } from "../components/DateFilterBar";
import {
  CurrencyStackedChart,
  FlagReasonsChart,
  FraudTrendChart,
  HorizontalBarChart,
  VerticalBarChart,
  formatNumber,
  formatPct,
  formatUsd,
} from "../components/charts";
import {
  ChartCard,
  DashboardCanvas,
  EmptyState,
  ErrorBanner,
  GranularityToggle,
  KpiCard,
  LoadingGrid,
  MetricColorLegend,
  NotReadyBanner,
  PageHeader,
} from "../components/ui";
import { useDateDrilldown } from "../hooks/useDateDrilldown";
import { canDrillTrend, filterTrendDataByDrill } from "../utils/datetimeAxis";

export function GeneralOverviewPage() {
  const [granularity, setGranularity] = useState<Granularity>("Yearly");
  const {
    drill,
    dateFilter,
    reset,
    setYear,
    applyTrendDrill,
    getTrendGranularity,
  } = useDateDrilldown();

  const trendGranularity = getTrendGranularity(granularity);
  const drillable = canDrillTrend(drill, trendGranularity);

  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const filterKey = [drill.year, drill.month];

  const kpis = useQuery({
    queryKey: ["general", "kpis", ...filterKey],
    queryFn: () => api.general.kpis(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const currency = useQuery({
    queryKey: ["general", "currency", ...filterKey],
    queryFn: () => api.general.currency(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const topUsers = useQuery({
    queryKey: ["general", "top-users", ...filterKey],
    queryFn: () => api.general.topUsers(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const merchantsCount = useQuery({
    queryKey: ["general", "merchants-count", ...filterKey],
    queryFn: () => api.general.merchantsByCount(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const merchantsRate = useQuery({
    queryKey: ["general", "merchants-rate", ...filterKey],
    queryFn: () => api.general.merchantsByRate(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const countriesCount = useQuery({
    queryKey: ["general", "countries-count", ...filterKey],
    queryFn: () => api.general.countriesByCount(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const countriesRate = useQuery({
    queryKey: ["general", "countries-rate", ...filterKey],
    queryFn: () => api.general.countriesByRate(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const flagReasons = useQuery({
    queryKey: ["general", "flag-reasons", ...filterKey],
    queryFn: () => api.general.flagReasons(dateFilter),
    enabled: meta.data?.general_ready,
  });
  const trends = useQuery({
    queryKey: ["general", "trends", trendGranularity, ...filterKey],
    queryFn: () => api.general.trends(trendGranularity, dateFilter),
    enabled: meta.data?.general_ready,
  });

  if (meta.isLoading) return <LoadingGrid />;
  if (!meta.data?.general_ready) return <NotReadyBanner />;

  const k = kpis.data;
  const reviewShare =
    k?.review_share_of_actions_pct ?? k?.review_share_of_flagged_pct ?? 0;

  const usersByCount = [...(topUsers.data ?? [])]
    .sort((a, b) => a.fraud_count - b.fraud_count)
    .slice(-10);
  const usersByAmount = [...(topUsers.data ?? [])]
    .sort((a, b) => a.fraud_amount_usd - b.fraud_amount_usd)
    .slice(-10);
  const merchantCountTop = [...(merchantsCount.data ?? [])]
    .sort((a, b) => a.fraud_count - b.fraud_count)
    .slice(-10);
  const merchantAmountTop = [...(merchantsCount.data ?? [])]
    .sort((a, b) => (a.fraud_amount_usd ?? 0) - (b.fraud_amount_usd ?? 0))
    .slice(-10);
  const merchantRateTop = [...(merchantsRate.data ?? [])]
    .sort((a, b) => a.fraud_rate_pct! - b.fraud_rate_pct!)
    .slice(-10);

  const trendSubtitle = drill.month
    ? "Daily view for selected month — click bars to inspect dates"
    : drill.year
      ? "Monthly view for selected year — click a month to drill down"
      : "Volume bars with fraud rate overlay — click a year or month to drill down";

  const trendData = filterTrendDataByDrill(trends.data ?? [], drill);

  return (
    <DashboardCanvas>
      <PageHeader
        title="General Fraud Overview"
        description="How severe is fraud exposure, and where is it concentrated?"
        actions={<MetricColorLegend />}
      />

      {kpis.isError ? <ErrorBanner message="Failed to load KPI marts." /> : null}

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <KpiCard label="Total Transactions" value={formatNumber(k?.total_tx)} tone="count" />
        <KpiCard
          label="Total Flagged"
          value={formatNumber(k?.flagged_count ?? k?.fraud_count)}
          hint="Auto-decline + review queue"
          tone="count"
        />
        <KpiCard
          label="Auto-Declined"
          value={formatNumber(k?.fraud_count)}
          hint="block + strong_suspect tiers"
          tone="count"
        />
        <KpiCard label="Fraud Rate" value={formatPct(k?.fraud_rate_pct)} tone="rate" />
        <KpiCard label="Sum Fraud Amount" value={formatUsd(k?.sum_fraud_amount_usd)} tone="amount" />
        <KpiCard
          label="Review Share of Actions"
          value={`${reviewShare.toFixed(1)}%`}
          hint="Manual review ÷ (review + auto-decline)"
          tone="rate"
        />
      </div>

      <div className="grid gap-3 xl:grid-cols-12">
        <ChartCard title="Legitimate vs Flagged by Currency" className="xl:col-span-3">
          {currency.data?.length ? (
            <CurrencyStackedChart data={currency.data} />
          ) : (
            <EmptyState message="No currency breakdown data yet." />
          )}
        </ChartCard>
        <ChartCard title="Top Users by Fraud-Flagged Count" className="xl:col-span-4">
          {usersByCount.length ? (
            <HorizontalBarChart
              data={usersByCount as unknown as Record<string, string | number>[]}
              xKey="fraud_count"
              yKey="user_id"
            />
          ) : (
            <EmptyState message="No fraud users in the lookback window." />
          )}
        </ChartCard>
        <ChartCard title="Top Users by Fraud-Flagged Amount (USD)" className="xl:col-span-5">
          {usersByAmount.length ? (
            <HorizontalBarChart
              data={usersByAmount as unknown as Record<string, string | number>[]}
              xKey="fraud_amount_usd"
              yKey="user_id"
            />
          ) : (
            <EmptyState message="No fraud users in the lookback window." />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Top Merchants by Fraud Count">
          {merchantCountTop.length ? (
            <HorizontalBarChart
              data={merchantCountTop as unknown as Record<string, string | number>[]}
              xKey="fraud_count"
              yKey="merchant_id"
            />
          ) : (
            <EmptyState message="No merchant fraud counts." />
          )}
        </ChartCard>
        <ChartCard title="Top Merchants by Fraud Amount (USD)">
          {merchantAmountTop.length ? (
            <HorizontalBarChart
              data={merchantAmountTop as unknown as Record<string, string | number>[]}
              xKey="fraud_amount_usd"
              yKey="merchant_id"
            />
          ) : (
            <EmptyState message="No merchant fraud amounts." />
          )}
        </ChartCard>
        <ChartCard title="Highest-Risk Merchants by Fraud Rate" subtitle="≥3 transactions">
          {merchantRateTop.length ? (
            <HorizontalBarChart
              data={merchantRateTop as unknown as Record<string, string | number>[]}
              xKey="fraud_rate_pct"
              yKey="merchant_id"
            />
          ) : (
            <EmptyState message="No merchants with ≥3 transactions for rate ranking." />
          )}
        </ChartCard>
      </div>

      <div className="grid gap-3 xl:grid-cols-3">
        <ChartCard title="Top Countries by Fraud Count">
          {(countriesCount.data?.length ?? 0) > 0 ? (
            <VerticalBarChart
              data={(countriesCount.data ?? []).slice(0, 10) as unknown as Record<string, string | number>[]}
              xKey="country"
              yKey="fraud_count"
            />
          ) : (
            <EmptyState message="No country fraud counts." />
          )}
        </ChartCard>
        <ChartCard title="Top Countries by Fraud Rate" subtitle="≥3 transactions">
          {(countriesRate.data?.length ?? 0) > 0 ? (
            <VerticalBarChart
              data={(countriesRate.data ?? []).slice(0, 10) as unknown as Record<string, string | number>[]}
              xKey="country"
              yKey="fraud_rate_pct"
            />
          ) : (
            <EmptyState message="No countries with ≥3 txns for rate ranking." />
          )}
        </ChartCard>
        <ChartCard title="Fraud Flag Count by Rule / Reason">
          {flagReasons.data?.length ? (
            <FlagReasonsChart data={flagReasons.data} />
          ) : (
            <EmptyState message="No rule-level flag reasons recorded yet." />
          )}
        </ChartCard>
      </div>

      <ChartCard
        title="Fraud Flagged Over Time"
        subtitle={trendSubtitle}
        actions={
          drill.year == null ? (
            <GranularityToggle value={granularity} onChange={setGranularity} />
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
          <EmptyState message="No trend data yet." />
        )}
      </ChartCard>
    </DashboardCanvas>
  );
}
