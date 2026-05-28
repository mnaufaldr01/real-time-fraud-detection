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
    <div className="mb-2 flex flex-wrap items-center gap-2 rounded-card border border-brand/25 bg-brand/5 px-3 py-2">
      <span className="text-[11px] font-semibold uppercase tracking-wide text-brand-dark">
        Trend period
      </span>
      <nav className="flex flex-wrap items-center gap-1 text-xs text-ink-mid">
        <FilterCrumb active={drill.month == null} onClick={onReset}>
          All data
        </FilterCrumb>
        <span className="text-ink-muted">/</span>
        <FilterCrumb active={drill.month == null} onClick={() => onSelectYear(drill.year!)}>
          {drill.year}
        </FilterCrumb>
        {monthLabel ? (
          <>
            <span className="text-ink-muted">/</span>
            <span className="rounded-[4px] bg-brand/15 px-2 py-0.5 font-medium text-brand-dark">
              {monthLabel}
            </span>
          </>
        ) : null}
      </nav>
      <button
        type="button"
        onClick={onReset}
        className="ml-auto inline-flex items-center gap-1.5 rounded-[4px] border border-surface-border bg-white px-2.5 py-1 text-[11px] font-medium text-ink-mid transition hover:border-brand/40 hover:text-brand-dark"
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
        "rounded-[4px] px-2 py-0.5 transition",
        active
          ? "bg-brand/15 font-medium text-brand-dark"
          : "text-ink-muted hover:bg-white hover:text-ink",
      )}
    >
      {children}
    </button>
  );
}
