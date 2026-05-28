import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { Granularity } from "../api/types";
import {
  CountryCharts,
  CurrencyStackedChart,
  FlagReasonsChart,
  FraudTrendChart,
  MerchantCharts,
  TopUsersCharts,
  formatNumber,
  formatPct,
  formatUsd,
} from "../components/charts";
import {
  ChartCard,
  EmptyState,
  ErrorBanner,
  GranularityToggle,
  KpiCard,
  LoadingGrid,
  NotReadyBanner,
  PageHeader,
  SectionDivider,
} from "../components/ui";

export function GeneralOverviewPage() {
  const [granularity, setGranularity] = useState<Granularity>("Daily");

  const meta = useQuery({ queryKey: ["meta"], queryFn: api.meta });
  const kpis = useQuery({ queryKey: ["general", "kpis"], queryFn: api.general.kpis, enabled: meta.data?.general_ready });
  const currency = useQuery({ queryKey: ["general", "currency"], queryFn: api.general.currency, enabled: meta.data?.general_ready });
  const topUsers = useQuery({ queryKey: ["general", "top-users"], queryFn: api.general.topUsers, enabled: meta.data?.general_ready });
  const merchantsCount = useQuery({ queryKey: ["general", "merchants-count"], queryFn: api.general.merchantsByCount, enabled: meta.data?.general_ready });
  const merchantsRate = useQuery({ queryKey: ["general", "merchants-rate"], queryFn: api.general.merchantsByRate, enabled: meta.data?.general_ready });
  const countriesCount = useQuery({ queryKey: ["general", "countries-count"], queryFn: api.general.countriesByCount, enabled: meta.data?.general_ready });
  const countriesRate = useQuery({ queryKey: ["general", "countries-rate"], queryFn: api.general.countriesByRate, enabled: meta.data?.general_ready });
  const flagReasons = useQuery({ queryKey: ["general", "flag-reasons"], queryFn: api.general.flagReasons, enabled: meta.data?.general_ready });
  const trends = useQuery({
    queryKey: ["general", "trends", granularity],
    queryFn: () => api.general.trends(granularity),
    enabled: meta.data?.general_ready,
  });

  if (meta.isLoading) return <LoadingGrid />;
  if (!meta.data?.general_ready) return <NotReadyBanner />;

  const k = kpis.data;
  const reviewShare =
    k?.review_share_of_actions_pct ?? k?.review_share_of_flagged_pct ?? 0;

  return (
    <div>
      <PageHeader
        title="General Fraud Overview"
        description="How severe is fraud exposure, and where is it concentrated across currencies, users, merchants, and geographies?"
      />

      {kpis.isError ? <ErrorBanner message="Failed to load KPI marts." /> : null}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6">
        <KpiCard label="Total Transactions" value={formatNumber(k?.total_tx)} />
        <KpiCard
          label="Total Flagged"
          value={formatNumber(k?.flagged_count ?? k?.fraud_count)}
          hint="Auto-decline + review queue"
          tone="warning"
        />
        <KpiCard
          label="Auto-Declined"
          value={formatNumber(k?.fraud_count)}
          hint="block + strong_suspect tiers"
          tone="danger"
        />
        <KpiCard label="Fraud Rate" value={formatPct(k?.fraud_rate_pct)} tone="danger" />
        <KpiCard label="Sum Fraud Amount" value={formatUsd(k?.sum_fraud_amount_usd)} tone="danger" />
        <KpiCard
          label="Review Share of Actions"
          value={`${reviewShare.toFixed(1)}%`}
          hint="Manual review ÷ (review + auto-decline)"
        />
      </div>

      <SectionDivider title="Currency & User Exposure" />

      <div className="grid gap-4 xl:grid-cols-3">
        <ChartCard title="Legitimate vs Flagged by Currency" className="xl:col-span-1">
          {currency.data?.length ? (
            <CurrencyStackedChart data={currency.data} />
          ) : (
            <EmptyState message="No currency breakdown data yet." />
          )}
        </ChartCard>
        <ChartCard
          title="Top Users by Fraud Exposure"
          subtitle="Count and USD amount for flagged transactions"
          className="xl:col-span-2"
        >
          {topUsers.data?.length ? (
            <TopUsersCharts data={topUsers.data} />
          ) : (
            <EmptyState message="No fraud users in the lookback window." />
          )}
        </ChartCard>
      </div>

      <SectionDivider title="Merchant Exposure" />

      <ChartCard title="Fraud Destination Merchants" subtitle="Count, amount, and rate rankings">
        {merchantsCount.data?.length ? (
          <MerchantCharts byCount={merchantsCount.data} byRate={merchantsRate.data ?? []} />
        ) : (
          <EmptyState message="No merchant fraud data yet." />
        )}
      </ChartCard>

      <SectionDivider title="Geographic Concentration" />

      <ChartCard title="Country Risk" subtitle="Top countries by fraud count and rate">
        {countriesCount.data?.length ? (
          <CountryCharts byCount={countriesCount.data} byRate={countriesRate.data ?? []} />
        ) : (
          <EmptyState message="No country fraud data yet." />
        )}
      </ChartCard>

      <SectionDivider title="Fraud by Rule Type" />

      <ChartCard title="Flag Reasons">
        {flagReasons.data?.length ? (
          <FlagReasonsChart data={flagReasons.data} />
        ) : (
          <EmptyState message="No rule-level flag reasons recorded yet." />
        )}
      </ChartCard>

      <SectionDivider title="Time Trend" />

      <div className="mb-4 flex justify-end">
        <GranularityToggle value={granularity} onChange={setGranularity} />
      </div>
      <ChartCard title="Fraud Flagged Over Time" subtitle="Volume bars with fraud rate overlay">
        {trends.data?.length ? (
          <FraudTrendChart data={trends.data} />
        ) : (
          <EmptyState message="No trend data yet." />
        )}
      </ChartCard>
    </div>
  );
}
