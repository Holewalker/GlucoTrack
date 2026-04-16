import { format } from "date-fns";
import { es } from "date-fns/locale";
import { useEvents } from "../hooks/useGlucoseData";
import type { Period } from "../api/client";

export function EventsTable({ period }: { period: Period }) {
  const { data, isLoading } = useEvents(period);

  if (isLoading) return <div className="events loading">Cargando…</div>;
  if (!data || data.length === 0)
    return <div className="events empty">Sin eventos en este período</div>;

  return (
    <div className="events">
      <h2>Eventos ({data.length})</h2>
      <table>
        <thead>
          <tr>
            <th>Tipo</th>
            <th>Inicio</th>
            <th>Duración</th>
            <th>Extremo</th>
          </tr>
        </thead>
        <tbody>
          {data.map((e, i) => (
            <tr key={i} className={e.type}>
              <td>
                <span className={`badge ${e.type}`}>
                  {e.type === "hypo" ? "Hipo" : "Hiper"}
                </span>
              </td>
              <td>
                {format(new Date(e.started_at), "dd/MM HH:mm", { locale: es })}
              </td>
              <td>{e.duration_min} min</td>
              <td style={{ color: e.type === "hypo" ? "#c05050" : "#c18937" }}>
                {e.extreme} mg/dL
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
