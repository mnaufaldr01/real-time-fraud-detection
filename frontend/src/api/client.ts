import type {
  CountryRow,
  CurrencyRow,
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

const API_BASE = import.meta.env.VITE_API_URL ?? "";

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  meta: () => fetchJson<MetaStatus>("/api/meta/status"),

  general: {
    kpis: () => fetchJson<GeneralKpis>("/api/general/kpis"),
    currency: () => fetchJson<CurrencyRow[]>("/api/general/currency"),
    topUsers: () => fetchJson<TopUserRow[]>("/api/general/top-users"),
    merchantsByCount: () => fetchJson<MerchantRow[]>("/api/general/merchants/by-count"),
    merchantsByRate: () => fetchJson<MerchantRow[]>("/api/general/merchants/by-rate"),
    countriesByCount: () => fetchJson<CountryRow[]>("/api/general/countries/by-count"),
    countriesByRate: () => fetchJson<CountryRow[]>("/api/general/countries/by-rate"),
    flagReasons: () => fetchJson<FlagReasonRow[]>("/api/general/flag-reasons"),
    trends: (granularity: Granularity) =>
      fetchJson<TrendRow[]>(`/api/general/trends?granularity=${granularity}`),
  },

  velocity: {
    kpis: () => fetchJson<VelocityKpis>("/api/velocity/kpis"),
    buckets: () => fetchJson<VelocityBucketRow[]>("/api/velocity/buckets"),
    topUsers: () => fetchJson<VelocityUserRow[]>("/api/velocity/top-users"),
    countriesByCount: () => fetchJson<CountryRow[]>("/api/velocity/countries/by-count"),
    countriesByRate: () => fetchJson<CountryRow[]>("/api/velocity/countries/by-rate"),
    scatter: () => fetchJson<VelocityScatterRow[]>("/api/velocity/scatter"),
    shareTrend: (granularity: Granularity) =>
      fetchJson<TrendRow[]>(`/api/velocity/share-trend?granularity=${granularity}`),
    heatmap: () => fetchJson<HeatmapRow[]>("/api/velocity/heatmap"),
    repeatInterval: () => fetchJson<IntervalRow[]>("/api/velocity/repeat-interval"),
    trends: (granularity: Granularity) =>
      fetchJson<TrendRow[]>(`/api/velocity/trends?granularity=${granularity}`),
  },
};
