/** Plotly YlOrRd stops for velocity heatmap parity with Streamlit. */
const YL_OR_RD: Array<[number, [number, number, number]]> = [
  [0, [255, 255, 204]],
  [0.125, [255, 237, 160]],
  [0.25, [254, 217, 118]],
  [0.375, [254, 178, 76]],
  [0.5, [253, 141, 60]],
  [0.625, [252, 78, 42]],
  [0.75, [227, 26, 28]],
  [0.875, [189, 0, 38]],
  [1, [128, 0, 38]],
];

function interpolateChannel(t: number, channel: 0 | 1 | 2): number {
  for (let i = 1; i < YL_OR_RD.length; i += 1) {
    const [t1, c1] = YL_OR_RD[i];
    if (t <= t1) {
      const [t0, c0] = YL_OR_RD[i - 1];
      const ratio = t1 === t0 ? 0 : (t - t0) / (t1 - t0);
      return Math.round(c0[channel] + ratio * (c1[channel] - c0[channel]));
    }
  }
  return YL_OR_RD[YL_OR_RD.length - 1][1][channel];
}

export function ylOrRdColor(intensity: number): string {
  const t = Math.max(0, Math.min(1, intensity));
  const r = interpolateChannel(t, 0);
  const g = interpolateChannel(t, 1);
  const b = interpolateChannel(t, 2);
  return `rgb(${r}, ${g}, ${b})`;
}

export function ylOrRdGradient(direction: "to top" | "to right" = "to top"): string {
  const stops = YL_OR_RD.map(([position, [r, g, b]]) => {
    const pct = (position * 100).toFixed(1);
    return `rgb(${r}, ${g}, ${b}) ${pct}%`;
  }).join(", ");
  return `linear-gradient(${direction}, ${stops})`;
}

export function heatmapIntensity(value: number, max: number): number {
  if (max <= 0 || value <= 0) return 0;
  return value / max;
}
