import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useHistory, useOverlay, useSettings } from "../hooks/useGlucoseData";
import { periodToRange } from "../api/client";
import type { Period } from "../api/client";

type GroupBy = "day" | "week" | "month";

function groupByForPeriod(period: Period): GroupBy {
  if (period === "1d" || period === "7d") return "day";
  if (period === "30d") return "week";
  return "month";
}

function generateTicks(from: number, to: number, period: Period): number[] {
  const ticks: number[] = [];
  const d = new Date(from);
  switch (period) {
    case "1d":
      d.setMinutes(0, 0, 0);
      while (d.getTime() <= to) { ticks.push(d.getTime()); d.setHours(d.getHours() + 3); }
      break;
    case "7d":
      while (d.getTime() <= to) { ticks.push(d.getTime()); d.setDate(d.getDate() + 1); }
      break;
    case "30d":
      while (d.getTime() <= to) { ticks.push(d.getTime()); d.setDate(d.getDate() + 5); }
      break;
    case "90d":
      while (d.getTime() <= to) { ticks.push(d.getTime()); d.setMonth(d.getMonth() + 1); }
      break;
  }
  return ticks;
}

function formatTick(ts: number, period: Period): string {
  const d = new Date(ts);
  switch (period) {
    case "1d":
      return format(d, "HH:mm", { locale: es });
    case "7d": {
      const s = format(d, "EEE", { locale: es });
      return s.charAt(0).toUpperCase() + s.slice(1);
    }
    case "30d":
      return format(d, "d", { locale: es });
    case "90d": {
      const s = format(d, "MMM", { locale: es });
      return s.charAt(0).toUpperCase() + s.slice(1);
    }
  }
}

function formatTooltipLabel(ts: number, period: Period): string {
  const d = new Date(ts);
  if (period === "1d") return format(d, "HH:mm", { locale: es });
  return format(d, "dd/MM HH:mm", { locale: es });
}

interface Props {
  period: Period;
}

export function GlucoseChart({ period }: Props) {
  const [overlayMode, setOverlayMode] = useState(false);
  const groupBy = groupByForPeriod(period);

  const { data: history } = useHistory(period);
  const { data: overlaySeries } = useOverlay(period, groupBy);
  const { data: settings } = useSettings();

  const TARGET_LOW = settings?.target_low ?? 60;
  const TARGET_HIGH = settings?.target_high ?? 140;

  const { from, to } = periodToRange(period);
  const fromTs = from.getTime();
  const toTs = to.getTime();
  const ticks = generateTicks(fromTs, toTs, period);

  const chartData = history?.map((r) => ({
    ts: new Date(r.timestamp).getTime(),
    value: r.value_mgdl,
  }));

  return (
    <div className="glucose-chart">
      <div className="chart-header">
        <h2>Glucosa</h2>
        {period !== "1d" && (
          <button
            onClick={() => setOverlayMode((v) => !v)}
            className={`toggle-btn ${overlayMode ? "active" : ""}`}
          >
            {overlayMode ? "Vista normal" : "Superponer períodos"}
          </button>
        )}
      </div>

      <ResponsiveContainer width="100%" height={300}>
        {overlayMode && overlaySeries ? (
          <LineChart margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="x" type="number" domain={["auto", "auto"]} />
            <YAxis domain={[40, 300]} />
            <Tooltip />
            <Legend />
            <ReferenceLine y={TARGET_LOW} stroke="#c05050" strokeDasharray="4 4" />
            <ReferenceLine y={TARGET_HIGH} stroke="#c18937" strokeDasharray="4 4" />
            {overlaySeries.map((series) => (
              <Line
                key={series.label}
                data={series.data}
                type="monotone"
                dataKey="value"
                name={series.label}
                stroke={series.color}
                dot={false}
                strokeWidth={2}
              />
            ))}
          </LineChart>
        ) : (
          <LineChart
            data={chartData}
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="ts"
              type="number"
              domain={[fromTs, toTs]}
              ticks={ticks}
              tickFormatter={(ts) => formatTick(ts, period)}
              tick={{ fontSize: 11 }}
            />
            <YAxis domain={[40, 300]} />
            <Tooltip
              labelFormatter={(ts) => formatTooltipLabel(Number(ts), period)}
            />
            <ReferenceLine y={TARGET_LOW} stroke="#c05050" strokeDasharray="4 4" label="Mín" />
            <ReferenceLine y={TARGET_HIGH} stroke="#c18937" strokeDasharray="4 4" label="Máx" />
            <Line
              type={period === "1d" ? "monotone" : "basis"}
              dataKey="value"
              stroke="#7d9e72"
              dot={false}
              strokeWidth={period === "1d" ? 2 : 1.5}
              name="mg/dL"
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
