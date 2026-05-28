function isAmountKey(key: string): boolean {
  return key.endsWith("_usd") || /(?:^|_)amount(?:_|$)/i.test(key);
}

function isPctKey(key: string): boolean {
  return key.endsWith("_pct") || /(?:^|_)(?:rate|share)(?:_|$)/i.test(key);
}

export function humanizeDataKey(key: string): string {
  const base = key.replace(/_usd$|_pct$/i, "");
  return base
    .split("_")
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");
}

export function formatTooltipAmount(value: number): string {
  return `$${Math.round(value).toLocaleString()}`;
}

export function formatTooltipPct(value: number): string {
  const rounded = Math.round(value * 10) / 10;
  return rounded % 1 === 0
    ? `${rounded.toFixed(0)}%`
    : `${rounded.toFixed(1)}%`;
}

export function formatTooltipValue(value: unknown, key: string): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value ?? "");

  if (isAmountKey(key)) return formatTooltipAmount(num);
  if (isPctKey(key)) return formatTooltipPct(num);
  return num.toLocaleString(undefined, { maximumFractionDigits: 2 });
}


function resolveDataKey(item: { dataKey?: unknown }, name: unknown): string {
  const key = item?.dataKey;
  if (typeof key === "string" || typeof key === "number") return String(key);
  return String(name ?? "");
}

export function chartTooltipFormatter(
  value: unknown,
  name: unknown,
  item?: { dataKey?: unknown; name?: unknown },
): [string, string] {
  const dataKey = resolveDataKey(item ?? {}, name);
  const itemName = item?.name == null ? undefined : String(item.name);
  const displayName =
    itemName && itemName !== dataKey ? itemName : humanizeDataKey(dataKey);

  return [formatTooltipValue(value, dataKey), displayName];
}

export const chartTooltipProps = {
  formatter: chartTooltipFormatter,
};
