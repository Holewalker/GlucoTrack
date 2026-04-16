import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { useHourlyPatterns, useSettings } from "../hooks/useGlucoseData";
import type { Period } from "../api/client";

export function HourlyPatterns({ period }: { period: Period }) {
  const { data, isLoading } = useHourlyPatterns(period);
  const { data: settings } = useSettings();

  const TARGET_LOW = settings?.target_low ?? 60;
  const TARGET_HIGH = settings?.target_high ?? 140;

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
          <ReferenceLine y={TARGET_LOW} stroke="#c05050" strokeDasharray="4 4" />
          <ReferenceLine y={TARGET_HIGH} stroke="#c18937" strokeDasharray="4 4" />
          <Bar dataKey="avg" fill="#7d9e72" name="Promedio" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
