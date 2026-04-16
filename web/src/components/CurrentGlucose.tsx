import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useCurrentGlucose } from "../hooks/useGlucoseData";

const TREND_ARROWS: Record<number, string> = {
  1: "↑↑",
  2: "↑",
  3: "→",
  4: "↓",
  5: "↓↓",
};

const TARGET_LOW = 60;
const TARGET_HIGH = 140;

function statusColor(value: number): string {
  if (value < TARGET_LOW) return "#c05050";
  if (value > TARGET_HIGH) return "#c18937";
  return "#6ea858";
}

export function CurrentGlucose() {
  const { data, isLoading, error } = useCurrentGlucose();

  if (isLoading) return <div className="current-glucose loading">Cargando…</div>;
  if (error || !data) return <div className="current-glucose error">Sin datos</div>;

  const color = statusColor(data.value_mgdl);
  const arrow = data.trend_arrow ? TREND_ARROWS[data.trend_arrow] ?? "?" : "?";
  const ago = formatDistanceToNow(new Date(data.timestamp), {
    addSuffix: true,
    locale: es,
  });

  return (
    <div className="current-glucose" style={{ borderColor: color }}>
      <span className="value" style={{ color }}>
        {data.value_mgdl} <span className="unit">mg/dL</span>
      </span>
      <span className="arrow" title="Tendencia">{arrow}</span>
      <span className="ago">Última lectura {ago}</span>
    </div>
  );
}
