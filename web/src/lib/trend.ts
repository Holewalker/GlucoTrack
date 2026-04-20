export const TREND_ARROWS: Record<number, string> = {
  1: "↓↓",
  2: "↘",
  3: "→",
  4: "↗",
  5: "↑↑",
};

export function trendArrowSymbol(arrow: number | null): string {
  if (!arrow) return "";
  return TREND_ARROWS[arrow] ?? "";
}
