import { useState } from "react";
import { format, startOfDay, endOfDay } from "date-fns";
import { useAlerts, useAlertStats, useUpdateAlertFeedback } from "../hooks/useGlucoseData";
import type { Alert } from "../api/client";

const LOCAL_DT = "yyyy-MM-dd'T'HH:mm:ss";

const CONF_LABEL: Record<string, string> = { high: "Alta", normal: "Normal", low: "Baja" };
const TYPE_LABEL: Record<string, string> = { hypo: "Hipo", hyper: "Hiper" };
const STATUS_LABEL: Record<string, string> = {
  active: "Activa",
  resolved: "Resuelta",
  expired: "Expirada",
};

function FeedbackCell({ alert }: { alert: Alert }) {
  const { mutate, isPending } = useUpdateAlertFeedback();
  if (alert.feedback === "accurate") return <span className="fb-pill fb-ok">✅ Acertada</span>;
  if (alert.feedback === "false_alarm") return <span className="fb-pill fb-false">❌ Falsa</span>;
  return (
    <span className="fb-actions">
      <button
        className="fb-btn"
        disabled={isPending}
        onClick={() => mutate({ id: alert.id, feedback: "accurate" })}
      >
        ✅
      </button>
      <button
        className="fb-btn"
        disabled={isPending}
        onClick={() => mutate({ id: alert.id, feedback: "false_alarm" })}
      >
        ❌
      </button>
    </span>
  );
}

export function AlertsPage() {
  const [from, setFrom] = useState(() => format(startOfDay(new Date()), LOCAL_DT));
  const [to, setTo] = useState(() => format(endOfDay(new Date()), LOCAL_DT));

  const { data: alerts = [], isLoading } = useAlerts({ start: from, end: to });
  const { data: stats } = useAlertStats({ start: from, end: to });

  const accuratePct =
    stats && stats.total > 0
      ? Math.round((stats.accurate_count / stats.total) * 100)
      : 0;
  const falsePct =
    stats && stats.total > 0
      ? Math.round((stats.false_alarm_count / stats.total) * 100)
      : 0;

  return (
    <main className="alerts-page">
      <h2>Historial de alertas</h2>

      <div className="rp-date-row">
        <label>
          Desde
          <input
            type="datetime-local"
            value={from.slice(0, 16)}
            onChange={(e) => setFrom(e.target.value + ":00")}
          />
        </label>
        <label>
          Hasta
          <input
            type="datetime-local"
            value={to.slice(0, 16)}
            onChange={(e) => setTo(e.target.value + ":00")}
          />
        </label>
      </div>

      {stats && (
        <div className="alerts-stats-row">
          <span>Total: {stats.total}</span>
          <span>Acertadas: {stats.accurate_count} ({accuratePct}%)</span>
          <span>Falsas: {stats.false_alarm_count} ({falsePct}%)</span>
          <span>Sin feedback: {stats.feedback_pending_count}</span>
        </div>
      )}

      {isLoading ? (
        <p>Cargando…</p>
      ) : alerts.length === 0 ? (
        <p className="rp-empty">Sin alertas en el período seleccionado.</p>
      ) : (
        <div className="rp-table-wrap">
          <table className="rp-table">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Tipo</th>
                <th>Valor</th>
                <th>Proyectado</th>
                <th>Min est.</th>
                <th>Confianza</th>
                <th>Estado</th>
                <th>Feedback</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>{a.created_at.slice(11, 16)}</td>
                  <td>
                    <span className={`conf-pill conf-${a.alert_type === "hyper" ? "normal" : "high"}`}>
                      {TYPE_LABEL[a.alert_type] ?? a.alert_type}
                    </span>
                  </td>
                  <td>{a.triggered_value} mg/dL</td>
                  <td>{a.projected_value} mg/dL</td>
                  <td>{Math.round(a.minutes_to_hypo)} min</td>
                  <td>
                    <span className={`conf-pill conf-${a.confidence}`}>
                      {CONF_LABEL[a.confidence] ?? a.confidence}
                    </span>
                  </td>
                  <td>{STATUS_LABEL[a.status] ?? a.status}</td>
                  <td>
                    <FeedbackCell alert={a} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  );
}
