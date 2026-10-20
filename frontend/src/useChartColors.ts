import { useEffect, useState } from "react";

// Recharts writes colours as SVG attributes, where CSS variables don't
// resolve, so read the current values and update when the theme changes.
const ROLES = ["series-1", "series-2", "grid", "text-secondary", "text-muted", "surface"] as const;
type Role = (typeof ROLES)[number];
export type ChartColors = Record<Role, string>;

function read(): ChartColors {
  const style = getComputedStyle(document.documentElement);
  return Object.fromEntries(ROLES.map((r) => [r, style.getPropertyValue(`--${r}`).trim() || "#888"])) as ChartColors;
}

export function useChartColors(): ChartColors {
  const [colors, setColors] = useState<ChartColors>(read);
  useEffect(() => {
    const media = window.matchMedia?.("(prefers-color-scheme: dark)");
    const update = () => setColors(read());
    media?.addEventListener?.("change", update);
    return () => media?.removeEventListener?.("change", update);
  }, []);
  return colors;
}
