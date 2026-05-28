import type {
  CountryRow,
  CurrencyRow,
  DateFilter,
  FlagReasonRow,
  GeneralKpis,
  Granularity,
  HeatmapRow,
  IntervalRow,
  MerchantRow,
  MetaStatus,
  TopUserRow,
  TrendRow,
  VelocityBucketRow,
  VelocityKpis,
  VelocityScatterRow,
  VelocityUserRow,
} from "./types";
import { fetchJson } from "./http";

export type { DateFilter, Granularity } from "./types";

export const liveApi = {
  meta: () => fetchJson<MetaStatus>("/api/meta/status"),

  general: {
    kpis: (filter?: DateFilter) => fetchJson<GeneralKpis>("/api/general/kpis", filter),
    currency: (filter?: DateFilter) => fetchJson<CurrencyRow[]>("/api/general/currency", filter),
    topUsers: (filter?: DateFilter) => fetchJson<TopUserRow[]>("/api/general/top-users", filter),
    merchantsByCount: (filter?: DateFilter) =>
      fetchJson<MerchantRow[]>("/api/general/merchants/by-count", filter),
    merchantsByRate: (filter?: DateFilter) =>
      fetchJson<MerchantRow[]>("/api/general/merchants/by-rate", filter),
    countriesByCount: (filter?: DateFilter) =>
      fetchJson<CountryRow[]>("/api/general/countries/by-count", filter),
    countriesByRate: (filter?: DateFilter) =>
      fetchJson<CountryRow[]>("/api/general/countries/by-rate", filter),
    flagReasons: (filter?: DateFilter) =>
      fetchJson<FlagReasonRow[]>("/api/general/flag-reasons", filter),
    trends: (granularity: Granularity, filter?: DateFilter) =>
      fetchJson<TrendRow[]>(`/api/general/trends?granularity=${granularity}`, filter),
  },

  velocity: {
    kpis: (filter?: DateFilter) => fetchJson<VelocityKpis>("/api/velocity/kpis", filter),
    buckets: (filter?: DateFilter) => fetchJson<VelocityBucketRow[]>("/api/velocity/buckets", filter),
    topUsers: (filter?: DateFilter) => fetchJson<VelocityUserRow[]>("/api/velocity/top-users", filter),
    countriesByCount: (filter?: DateFilter) =>
      fetchJson<CountryRow[]>("/api/velocity/countries/by-count", filter),
    countriesByRate: (filter?: DateFilter) =>
      fetchJson<CountryRow[]>("/api/velocity/countries/by-rate", filter),
    scatter: (filter?: DateFilter) => fetchJson<VelocityScatterRow[]>("/api/velocity/scatter", filter),
    shareTrend: (granularity: Granularity, filter?: DateFilter) =>
      fetchJson<TrendRow[]>(`/api/velocity/share-trend?granularity=${granularity}`, filter),
    heatmap: (filter?: DateFilter) => fetchJson<HeatmapRow[]>("/api/velocity/heatmap", filter),
    repeatInterval: (filter?: DateFilter) =>
      fetchJson<IntervalRow[]>("/api/velocity/repeat-interval", filter),
    trends: (granularity: Granularity, filter?: DateFilter) =>
      fetchJson<TrendRow[]>(`/api/velocity/trends?granularity=${granularity}`, filter),
  },
};
