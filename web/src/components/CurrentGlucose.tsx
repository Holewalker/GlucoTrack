import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";
import { useCurrentGlucose, useSettings } from "../hooks/useGlucoseData";

const TREND_ARROWS: Record<number, string> = {
  1: "↑↑",
  2: "↑",
  3: "→",
  4: "↓",
  5: "↓↓",
};

function statusColor(value: number, targetLow: number, targetHigh: number): string {
  if (value < targetLow) return "#c05050";
  if (value > targetHigh) return "#c18937";
  return "#6ea858";
}

export function CurrentGlucose() {
  const { data, isLoading, error } = useCurrentGlucose();
  const { data: settings } = useSettings();

  if (isLoading) return <div className="current-glucose loading">Cargando…</div>;
  if (error || !data) return <div className="current-glucose error">Sin datos</div>;

  const color = statusColor(data.value_mgdl, settings?.target_low ?? 60, settings?.target_high ?? 140);
  const arrow = data.trend_arrow ? (TREND_ARROWS[data.trend_arrow] ?? null) : null;
  const ago = formatDistanceToNow(new Date(data.timestamp), {
    addSuffix: true,
    locale: es,
  });

  return (
    <div className="current-glucose" style={{ borderColor: color }}>
      <span className="value" style={{ color }}>
        {data.value_mgdl} <span className="unit">mg/dL</span>
      </span>
      {arrow && <span className="arrow" title="Tendencia">{arrow}</span>}
      <span className="ago">Última lectura {ago}</span>
    </div>
  );
}
