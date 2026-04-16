import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { useTimeInRange } from "../hooks/useGlucoseData";
import type { Period } from "../api/client";

const COLORS: Record<string, string> = {
  "En rango": "#6ea858",
  "Alto": "#c18937",
  "Bajo": "#c05050",
};

export function TimeInRange({ period }: { period: Period }) {
  const { data, isLoading } = useTimeInRange(period);

  if (isLoading || !data) return <div className="tir loading">Cargando…</div>;

  const chartData = [
    { name: "En rango", value: data.in_range_pct },
    { name: "Alto", value: data.high_pct },
    { name: "Bajo", value: data.low_pct },
  ];

  return (
    <div className="tir">
      <h2>Tiempo en rango</h2>
      <p className="tir-main">{data.in_range_pct}% en rango</p>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70}>
            {chartData.map((entry) => (
              <Cell key={entry.name} fill={COLORS[entry.name]} />
            ))}
          </Pie>
          <Tooltip formatter={(v: unknown) => `${v}%`} />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
      <p className="tir-detail">
        <span style={{ color: "#c18937" }}>Alto {data.high_pct}%</span>
        {" · "}
        <span style={{ color: "#c05050" }}>Bajo {data.low_pct}%</span>
      </p>
    </div>
  );
}
