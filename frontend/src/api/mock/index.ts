import type { DateFilter, Granularity } from "../types";
import {
  mockCountriesByCount,
  mockCountriesByRate,
  mockCurrency,
  mockFlagReasons,
  mockGeneralKpis,
  mockGeneralTrends,
  mockHeatmap,
  mockMerchantsByCount,
  mockMerchantsByRate,
  mockMeta,
  mockRepeatInterval,
  mockScatter,
  mockTopUsers,
  mockVelocityBuckets,
  mockVelocityCountriesCount,
  mockVelocityCountriesRate,
  mockVelocityKpis,
  mockVelocityShareTrend,
  mockVelocityTrends,
  mockVelocityUsers,
} from "./data";

const MOCK_DELAY_MS = 120;

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => {
    window.setTimeout(() => resolve(value), MOCK_DELAY_MS);
  });
}

/** Demo API — same shape as the live client; ignores date filters (static sample). */
export const mockApi = {
  meta: () => delay({ ...mockMeta }),

  general: {
    kpis: (_filter?: DateFilter) => delay({ ...mockGeneralKpis }),
    currency: (_filter?: DateFilter) => delay([...mockCurrency]),
    topUsers: (_filter?: DateFilter) => delay([...mockTopUsers]),
    merchantsByCount: (_filter?: DateFilter) => delay([...mockMerchantsByCount]),
    merchantsByRate: (_filter?: DateFilter) => delay([...mockMerchantsByRate]),
    countriesByCount: (_filter?: DateFilter) => delay([...mockCountriesByCount]),
    countriesByRate: (_filter?: DateFilter) => delay([...mockCountriesByRate]),
    flagReasons: (_filter?: DateFilter) => delay([...mockFlagReasons]),
    trends: (granularity: Granularity, _filter?: DateFilter) =>
      delay(mockGeneralTrends(granularity)),
  },

  velocity: {
    kpis: (_filter?: DateFilter) => delay({ ...mockVelocityKpis }),
    buckets: (_filter?: DateFilter) => delay([...mockVelocityBuckets]),
    topUsers: (_filter?: DateFilter) => delay([...mockVelocityUsers]),
    countriesByCount: (_filter?: DateFilter) => delay([...mockVelocityCountriesCount]),
    countriesByRate: (_filter?: DateFilter) => delay([...mockVelocityCountriesRate]),
    scatter: (_filter?: DateFilter) => delay([...mockScatter]),
    shareTrend: (granularity: Granularity, _filter?: DateFilter) =>
      delay(mockVelocityShareTrend(granularity)),
    heatmap: (_filter?: DateFilter) => delay([...mockHeatmap]),
    repeatInterval: (_filter?: DateFilter) => delay([...mockRepeatInterval]),
    trends: (granularity: Granularity, _filter?: DateFilter) =>
      delay(mockVelocityTrends(granularity)),
  },
};
