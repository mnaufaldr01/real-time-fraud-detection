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
    <div className="card p-4 shadow-glow/20 transition hover:border-accent/40">
      <p className="muted mb-1">{label}</p>
      <p className={clsx("font-display text-2xl font-bold tracking-tight", toneStyles[tone])}>
        {value}
      </p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </div>
  );
}

interface ChartCardProps {
  title: string;
  subtitle?: string;
  children: ReactNode;
  className?: string;
}

export function ChartCard({ title, subtitle, children, className }: ChartCardProps) {
  return (
    <div className={clsx("card p-4", className)}>
      <div className="mb-4">
        <h3 className="section-title">{title}</h3>
        {subtitle ? <p className="muted mt-1">{subtitle}</p> : null}
      </div>
      <div className="min-h-[260px]">{children}</div>
    </div>
  );
}

interface EmptyStateProps {
  message: string;
}

export function EmptyState({ message }: EmptyStateProps) {
  return (
    <div className="flex h-[240px] items-center justify-center rounded-lg border border-dashed border-surface-border/60 bg-slate-900/30">
      <p className="muted px-4 text-center">{message}</p>
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
    <div className="inline-flex rounded-lg border border-surface-border bg-slate-900/50 p-1">
      {OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={clsx(
            "rounded-md px-3 py-1.5 text-xs font-medium transition",
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
    <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 className="font-display text-3xl font-bold tracking-tight text-white">{title}</h1>
        <p className="muted mt-2 max-w-3xl">{description}</p>
      </div>
      {actions}
    </div>
  );
}

export function SectionDivider({ title }: { title: string }) {
  return (
    <div className="my-8 flex items-center gap-3">
      <h2 className="section-title whitespace-nowrap">{title}</h2>
      <div className="h-px flex-1 bg-gradient-to-r from-surface-border to-transparent" />
    </div>
  );
}

export function LoadingGrid() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {Array.from({ length: 6 }).map((_, index) => (
        <div key={index} className="card h-72 animate-pulse bg-slate-800/40" />
      ))}
    </div>
  );
}

export function ErrorBanner({ message }: { message: string }) {
  return (
    <div className="mb-6 rounded-xl border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-red-200">
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
