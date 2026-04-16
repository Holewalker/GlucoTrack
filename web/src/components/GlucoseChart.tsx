import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from "recharts";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useHistory, useOverlay } from "../hooks/useGlucoseData";
import type { Period } from "../api/client";

const TARGET_LOW = 60;
const TARGET_HIGH = 140;

type GroupBy = "day" | "week" | "month";

function groupByForPeriod(period: Period): GroupBy {
  if (period === "1d" || period === "7d") return "day";
  if (period === "30d") return "week";
  return "month";
}

interface Props {
  period: Period;
}

export function GlucoseChart({ period }: Props) {
  const [overlayMode, setOverlayMode] = useState(false);
  const groupBy = groupByForPeriod(period);

  const { data: history } = useHistory(period);
  const { data: overlaySeries } = useOverlay(period, groupBy);

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
            data={history?.map((r) => ({
              time: format(new Date(r.timestamp), "HH:mm dd/MM", { locale: es }),
              value: r.value_mgdl,
            }))}
            margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="time" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
            <YAxis domain={[40, 300]} />
            <Tooltip />
            <ReferenceLine y={TARGET_LOW} stroke="#c05050" strokeDasharray="4 4" label="Mín" />
            <ReferenceLine y={TARGET_HIGH} stroke="#c18937" strokeDasharray="4 4" label="Máx" />
            <Line
              type="monotone"
              dataKey="value"
              stroke="#7d9e72"
              dot={false}
              strokeWidth={2}
              name="mg/dL"
            />
          </LineChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
