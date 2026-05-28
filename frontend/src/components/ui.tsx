import clsx from "clsx";
import type { ReactNode } from "react";
import type { Granularity } from "../api/types";
import { METRIC_COLORS } from "../theme/palette";

interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "count" | "amount" | "rate" | "success";
}

const toneStyles = {
  default: "text-ink",
  count: "text-brand",
  amount: "text-[#F5A623]",
  rate: "text-brand-dark",
  success: "text-success",
};

export function KpiCard({ label, value, hint, tone = "default" }: KpiCardProps) {
  return (
    <div className="card p-3">
      <p className="mb-0.5 text-[0.7rem] font-semibold uppercase tracking-wide text-ink-muted">
        {label}
      </p>
      <p className={clsx("text-xl font-extrabold leading-tight", toneStyles[tone])}>{value}</p>
      {hint ? <p className="mt-1 text-[0.65rem] leading-tight text-ink-muted">{hint}</p> : null}
    </div>
  );
}

interface ChartCardProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function ChartCard({ title, subtitle, actions, children, className }: ChartCardProps) {
  return (
    <div className={clsx("card flex flex-col gap-2 overflow-hidden p-3.5", className)}>
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="card-title">{title}</h3>
          {subtitle ? <p className="mt-0.5 text-[0.75rem] text-ink-muted">{subtitle}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
      <div className="min-h-[210px] flex-1 overflow-visible">{children}</div>
    </div>
  );
}

interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="flex h-[190px] items-center justify-center rounded-card border border-dashed border-surface-border bg-[#FAFAFA]">
      <p className="muted px-4 text-center text-xs">{message}</p>
    </div>
  );
}

interface GranularityToggleProps {
  value: Granularity;
  onChange: (value: Granularity) => void;
}

const OPTIONS: Granularity[] = ["Daily", "Monthly", "Yearly"];

export function GranularityToggle({ value, onChange }: GranularityToggleProps) {
  return (
    <div className="inline-flex rounded-card border border-surface-border bg-[#FAFAFA] p-0.5">
      {OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={clsx(
            "rounded-[4px] px-2 py-1 text-[10px] font-semibold transition",
            value === option
              ? "bg-brand text-white"
              : "text-ink-muted hover:bg-white hover:text-ink",
          )}
        >
          {option}
        </button>
      ))}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-1 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="section-title">{title}</h1>
        <p className="mt-0.5 max-w-3xl text-xs text-ink-muted">{description}</p>
      </div>
      {actions}
    </div>
  );
}

export function DashboardCanvas({ children }: { children: ReactNode }) {
  return <div className="space-y-3">{children}</div>;
}

export function MetricColorLegend() {
  const items = [
    { label: "Counts", color: METRIC_COLORS.count },
    { label: "Amounts", color: METRIC_COLORS.amount },
    { label: "Rates / %", color: METRIC_COLORS.rate },
  ] as const;

  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-ink-muted">
      {items.map((item) => (
        <li key={item.label} className="flex items-center gap-1.5">
          <span
            className="inline-block h-2.5 w-2.5 rounded-full"
            style={{ backgroundColor: item.color }}
          />
          {item.label}
        </li>
      ))}
    </ul>
  );
}

export function LoadingGrid() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="card h-52 animate-pulse bg-[#EBEBEB]" />
      ))}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-3 rounded-card border border-danger/30 bg-danger/10 px-4 py-2 text-sm text-danger">
      {message}
    </div>
  );
}

export function NotReadyBanner() {
  return (
    <div className="card border-l-4 border-brand-pale bg-white p-6">
      <h2 className="text-lg font-bold text-brand-dark">Analytics marts not ready</h2>
      <p className="muted mt-2 text-ink-mid">
        Run <code className="rounded bg-surface px-1.5 py-0.5 text-brand-dark">dbt run</code> in{" "}
        <code className="rounded bg-surface px-1.5 py-0.5 text-brand-dark">dbt_fraud/</code> after
        Postgres has transaction data, or enable the Airflow{" "}
        <code className="rounded bg-surface px-1.5 py-0.5 text-brand-dark">dbt_marts_refresh</code>{" "}
        DAG.
      </p>
    </div>
  );
}
