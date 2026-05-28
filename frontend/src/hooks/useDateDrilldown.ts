import { useCallback, useMemo, useState } from "react";
import type { DateDrilldown, DateFilter, Granularity } from "../api/types";
import {
  drillFromTrendPoint,
  effectiveTrendGranularity,
  toDateFilter,
} from "../utils/datetimeAxis";

export function useDateDrilldown() {
  const [drill, setDrill] = useState<DateDrilldown>({ year: null, month: null });

  const reset = useCallback(() => {
    setDrill({ year: null, month: null });
  }, []);

  const setYear = useCallback((year: number) => {
    setDrill({ year, month: null });
  }, []);

  const setYearMonth = useCallback((year: number, month: number) => {
    setDrill({ year, month });
  }, []);

  const applyTrendDrill = useCallback(
    (reportDate: string, viewGranularity: Granularity) => {
      const next = drillFromTrendPoint(drill, viewGranularity, reportDate);
      if (next) setDrill(next);
    },
    [drill],
  );

  const dateFilter: DateFilter | undefined = useMemo(() => toDateFilter(drill), [drill]);

  const isFiltered = drill.year != null;

  const getTrendGranularity = useCallback(
    (manualGranularity: Granularity) => effectiveTrendGranularity(drill, manualGranularity),
    [drill],
  );

  return {
    drill,
    dateFilter,
    isFiltered,
    reset,
    setYear,
    setYearMonth,
    applyTrendDrill,
    getTrendGranularity,
  };
}
