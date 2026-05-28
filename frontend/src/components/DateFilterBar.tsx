import clsx from "clsx";
import type { ReactNode } from "react";
import { RotateCcw } from "lucide-react";
import type { DateDrilldown } from "../api/types";
import { formatMonthYear } from "../utils/datetimeAxis";

interface DateFilterBarProps {
  drill: DateDrilldown;
  onReset: () => void;
  onSelectYear: (year: number) => void;
}

export function DateFilterBar({ drill, onReset, onSelectYear }: DateFilterBarProps) {
  if (drill.year == null) {
    return null;
  }

  const monthLabel =
    drill.month != null ? formatMonthYear(new Date(drill.year, drill.month - 1, 1)) : null;

  return (
    <div className="mb-2 flex flex-wrap items-center gap-2 rounded-lg border border-accent/30 bg-accent/10 px-3 py-2">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-accent">
        Trend period
      </span>
      <nav className="flex flex-wrap items-center gap-1 text-xs text-slate-300">
        <FilterCrumb active={drill.month == null} onClick={onReset}>
          All data
        </FilterCrumb>
        <span className="text-slate-600">/</span>
        <FilterCrumb
          active={drill.month == null}
          onClick={() => onSelectYear(drill.year!)}
        >
          {drill.year}
        </FilterCrumb>
        {monthLabel ? (
          <>
            <span className="text-slate-600">/</span>
            <span className="rounded-md bg-accent/20 px-2 py-0.5 font-medium text-accent">
              {monthLabel}
            </span>
          </>
        ) : null}
      </nav>
      <button
        type="button"
        onClick={onReset}
        className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-surface-border bg-slate-900/70 px-2.5 py-1 text-[11px] font-medium text-slate-200 transition hover:border-accent/50 hover:text-white"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        Reset
      </button>
    </div>
  );
}

function FilterCrumb({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "rounded-md px-2 py-0.5 transition",
        active
          ? "bg-accent/20 font-medium text-accent"
          : "text-slate-400 hover:bg-slate-800/70 hover:text-white",
      )}
    >
      {children}
    </button>
  );
}
