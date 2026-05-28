import type { DateFilter } from "./types";

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export function dateFilterQuery(filter?: DateFilter): string {
  if (!filter?.year) return "";
  const params = new URLSearchParams();
  params.set("year", String(filter.year));
  if (filter.month != null) {
    params.set("month", String(filter.month));
  }
  return params.toString();
}

export function appendQuery(path: string, filter?: DateFilter): string {
  const query = dateFilterQuery(filter);
  if (!query) return path;
  return path.includes("?") ? `${path}&${query}` : `${path}?${query}`;
}

export async function fetchJson<T>(path: string, filter?: DateFilter): Promise<T> {
  const response = await fetch(`${API_BASE}${appendQuery(path, filter)}`);
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}
