export interface GlucoseReading {
  id: number;
  timestamp: string;
  value_mgdl: number;
  trend_arrow: number | null;
  is_high: boolean;
  is_low: boolean;
  measurement_color: number | null;
}

export interface TimeInRange {
  total: number;
  in_range_pct: number;
  high_pct: number;
  low_pct: number;
}

export interface HourlyPattern {
  hour: number;
  avg: number;
  min: number;
  max: number;
}

export interface GlucoseEvent {
  type: "hypo" | "hyper";
  started_at: string;
  ended_at: string;
  duration_min: number;
  extreme: number;
}

export interface OverlaySeries {
  label: string;
  color: string;
  data: Array<{ x: number; value: number }>;
}

export type Period = "1d" | "7d" | "30d" | "90d";

function periodToDates(period: Period): { from: string; to: string } {
  const to = new Date();
  const from = new Date(to);
  const days: Record<Period, number> = { "1d": 1, "7d": 7, "30d": 30, "90d": 90 };
  from.setDate(from.getDate() - days[period]);
  return { from: from.toISOString(), to: to.toISOString() };
}

const BASE = "/api";

async function get<T>(path: string, params?: Record<string, string>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  current: () => get<GlucoseReading>("/glucose/current"),
  history: (period: Period) => {
    const { from, to } = periodToDates(period);
    return get<GlucoseReading[]>("/glucose/history", { from, to });
  },
  timeInRange: (period: Period) => {
    const { from, to } = periodToDates(period);
    return get<TimeInRange>("/stats/time-in-range", { from, to });
  },
  hourlyPatterns: (period: Period) => {
    const { from, to } = periodToDates(period);
    return get<HourlyPattern[]>("/stats/hourly-patterns", { from, to });
  },
  events: (period: Period) => {
    const { from, to } = periodToDates(period);
    return get<GlucoseEvent[]>("/stats/events", { from, to });
  },
  overlay: (period: Period, groupBy: "day" | "week" | "month") => {
    const { from, to } = periodToDates(period);
    return get<OverlaySeries[]>("/glucose/overlay", { from, to, group_by: groupBy });
  },
};
