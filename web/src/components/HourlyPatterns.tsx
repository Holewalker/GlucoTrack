import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useHourlyPatterns } from "../hooks/useGlucoseData";
import type { Period } from "../api/client";

const TARGET_LOW = 60;
const TARGET_HIGH = 140;

export function HourlyPatterns({ period }: { period: Period }) {
  const { data, isLoading } = useHourlyPatterns(period);

  if (isLoading || !data) return <div className="hourly loading">Cargando…</div>;

  return (
    <div className="hourly">
      <h2>Patrones por hora del día</h2>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="hour" tickFormatter={(h: number) => `${h}h`} />
          <YAxis domain={[40, 300]} />
          <Tooltip
            formatter={(v: unknown) => [`${v} mg/dL`]}
            labelFormatter={(h: unknown) => `${h}:00hs`}
          />
          <ReferenceLine y={TARGET_LOW} stroke="#ef4444" strokeDasharray="4 4" />
          <ReferenceLine y={TARGET_HIGH} stroke="#f59e0b" strokeDasharray="4 4" />
          <Bar dataKey="avg" fill="#3b82f6" name="Promedio" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
