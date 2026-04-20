import {
  startOfDay, endOfDay, startOfWeek, endOfWeek,
  startOfMonth, endOfMonth, subMonths, format,
} from "date-fns";

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

export interface Settings {
  target_low: number;
  target_high: number;
  predictor_enabled: number;
  prediction_window_minutes: number;
  lookback_minutes: number;
  min_readings: number;
  alert_cooldown_minutes: number;
  telegram_bot_token_set: boolean;
}

export interface Alert {
  id: number;
  alert_type: "hypo" | "hyper";
  created_at: string;
  triggered_value: number;
  projected_value: number;
  minutes_to_hypo: number;
  slope: number;
  confidence: "high" | "normal" | "low";
  trend_arrow: number | null;
  status: "active" | "resolved" | "expired";
  resolved_at: string | null;
  telegram_sent: boolean;
  feedback: "accurate" | "false_alarm" | null;
  live_current_value?: number;
  live_projected_value?: number;
  live_minutes_to_hypo?: number;
  live_slope?: number;
  live_confidence?: "high" | "normal" | "low";
  live_trend_arrow?: number | null;
}

export interface AlertStats {
  total: number;
  accurate_count: number;
  false_alarm_count: number;
  feedback_pending_count: number;
}

export interface TelegramRecipient {
  id: number;
  chat_id: string;
  label: string;
  enabled: number;
  created_at: string;
}

export type Period = "1d" | "7d" | "30d" | "90d";

export function periodToRange(period: Period): { from: Date; to: Date } {
  const now = new Date();
  switch (period) {
    case "1d":
      return { from: startOfDay(now), to: endOfDay(now) };
    case "7d":
      return { from: startOfWeek(now, { weekStartsOn: 1 }), to: endOfWeek(now, { weekStartsOn: 1 }) };
    case "30d":
      return { from: startOfMonth(now), to: endOfMonth(now) };
    case "90d":
      return { from: startOfMonth(subMonths(now, 2)), to: endOfMonth(now) };
  }
}

const LOCAL_DT = "yyyy-MM-dd'T'HH:mm:ss";

function periodToDates(period: Period): { from: string; to: string } {
  const { from, to } = periodToRange(period);
  return { from: format(from, LOCAL_DT), to: format(to, LOCAL_DT) };
}

const PERIOD_BIN_MINUTES: Record<Period, number> = {
  "1d":  0,   // raw
  "7d":  30,  // 30-min bins → ~336 pts
  "30d": 60,  // 1-hour bins → ~720 pts
  "90d": 180, // 3-hour bins → ~720 pts
};

const BASE = "/api";

async function get<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(BASE + path, window.location.origin);
  if (params) Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)));
  const res = await fetch(url.toString());
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(BASE + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  if (res.status === 204) return undefined as T;
  return res.json();
}

async function deleteReq(path: string): Promise<void> {
  const res = await fetch(BASE + path, { method: "DELETE" });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
}

export const api = {
  settings: () => get<Settings>("/settings"),
  updateSettings: (data: Partial<Settings>) => patch<Settings>("/settings", data),
  current: () => get<GlucoseReading>("/glucose/current"),
  history: (period: Period) => {
    const { from, to } = periodToDates(period);
    const bin_minutes = PERIOD_BIN_MINUTES[period];
    return get<GlucoseReading[]>("/glucose/history", bin_minutes > 0 ? { from, to, bin_minutes } : { from, to });
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
  // Alerts
  activeAlert: () => get<Alert>("/alerts/active"),
  alerts: (params?: Record<string, string>) => get<Alert[]>("/alerts", params),
  alertStats: (params?: Record<string, string>) => get<AlertStats>("/alerts/stats", params),
  patchAlertFeedback: (id: number, feedback: string) =>
    patch<Alert>(`/alerts/${id}`, { feedback }),
  // Telegram recipients
  telegramRecipients: () => get<TelegramRecipient[]>("/telegram/recipients"),
  createRecipient: (data: { chat_id: string; label: string; enabled?: number }) =>
    post<TelegramRecipient>("/telegram/recipients", data),
  updateRecipient: (id: number, data: Partial<TelegramRecipient>) =>
    patch<TelegramRecipient>(`/telegram/recipients/${id}`, data),
  deleteRecipient: (id: number) => deleteReq(`/telegram/recipients/${id}`),
  detectChatId: () => post<{ chat_id: string; name: string; type: string }[]>("/telegram/detect-chat-id"),
  sendTest: () => post<{ results: { chat_id: string; label: string; sent: boolean }[] }>("/telegram/test"),
};
