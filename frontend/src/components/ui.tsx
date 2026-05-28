import clsx from "clsx";
import type { ReactNode } from "react";
import type { Granularity } from "../api/types";

interface KpiCardProps {
  label: string;
  value: string;
  hint?: string;
  tone?: "default" | "danger" | "success" | "warning";
}

const toneStyles = {
  default: "text-white",
  danger: "text-danger",
  success: "text-success",
  warning: "text-warning",
};

export function KpiCard({ label, value, hint, tone = "default" }: KpiCardProps) {
  return (
    <div className="card p-3 shadow-glow/20 transition hover:border-accent/40">
      <p className="mb-0.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </p>
      <p className={clsx("font-display text-xl font-bold tracking-tight", toneStyles[tone])}>
        {value}
      </p>
      {hint ? <p className="mt-1 text-[10px] leading-tight text-slate-500">{hint}</p> : null}
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
    <div className={clsx("card p-3", className)}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold tracking-tight text-white">{title}</h3>
          {subtitle ? <p className="mt-0.5 text-[11px] text-slate-500">{subtitle}</p> : null}
        </div>
        {actions ? <div className="shrink-0">{actions}</div> : null}
      </div>
      <div className="min-h-[210px]">{children}</div>
    </div>
  );
}

interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="flex h-[190px] items-center justify-center rounded-lg border border-dashed border-surface-border/60 bg-slate-900/30">
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
    <div className="inline-flex rounded-md border border-surface-border bg-slate-900/50 p-0.5">
      {OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={clsx(
            "rounded px-2 py-1 text-[10px] font-medium transition",
            value === option
              ? "bg-accent text-slate-950"
              : "text-slate-400 hover:text-white",
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
    <div className="mb-3 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 className="font-display text-lg font-bold tracking-tight text-white">{title}</h1>
        <p className="mt-0.5 max-w-3xl text-xs text-slate-400">{description}</p>
      </div>
      {actions}
    </div>
  );
}

/** Tight vertical rhythm for single-page Power BI–style canvases. */
export function DashboardCanvas({ children }: { children: ReactNode }) {
  return <div className="space-y-3">{children}</div>;
}

export function LoadingGrid() {
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="card h-52 animate-pulse bg-slate-800/40" />
      ))}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-3 rounded-xl border border-danger/40 bg-danger/10 px-4 py-2 text-sm text-red-200">
      {message}
    </div>
  );
}

export function NotReadyBanner() {
  return (
    <div className="card border-warning/30 bg-warning/10 p-6">
      <h2 className="font-display text-lg font-semibold text-warning">Analytics marts not ready</h2>
      <p className="muted mt-2">
        Run <code className="rounded bg-slate-800 px-1.5 py-0.5 text-accent">dbt run</code> in{" "}
        <code className="rounded bg-slate-800 px-1.5 py-0.5 text-accent">dbt_fraud/</code> after
        Postgres has transaction data, or enable the Airflow{" "}
        <code className="rounded bg-slate-800 px-1.5 py-0.5 text-accent">dbt_marts_refresh</code>{" "}
        DAG.
      </p>
    </div>
  );
}
