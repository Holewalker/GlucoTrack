import { useState, useMemo } from "react";
import { format, startOfDay, eachDayOfInterval, isToday } from "date-fns";
import { es } from "date-fns/locale";
import { useHistory, useSettings } from "../hooks/useGlucoseData";
import { periodToRange } from "../api/client";
import type { Period } from "../api/client";
import { trendArrowSymbol } from "../lib/trend";

interface Props {
  period: Period;
  onBack: () => void;
}

export function RecordsPage({ period, onBack }: Props) {
  const { from: rangeFrom, to: rangeTo } = periodToRange(period);
  const days = eachDayOfInterval({ start: rangeFrom, end: rangeTo }).reverse();

  const [selectedDay, setSelectedDay] = useState<Date>(days[0]);
  const dayStart = startOfDay(selectedDay);

  const { data: settings } = useSettings();
  const { data: allData, isLoading } = useHistory(period);
  const targetLow = settings?.target_low ?? 60;
  const targetHigh = settings?.target_high ?? 180;

  const sorted = useMemo(() => {
    if (!allData) return [];
    return allData
      .filter((r) => startOfDay(new Date(r.timestamp)).getTime() === dayStart.getTime())
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [allData, dayStart]);

  const showDaySelector = period !== "1d";

  return (
    <div className="records-page">
      <div className="records-header">
        <button className="records-back" onClick={onBack}>
          ← Volver
        </button>
        <h2>
          Registros — {isToday(selectedDay)
            ? "Hoy"
            : format(selectedDay, "EEEE d 'de' MMMM", { locale: es })}
        </h2>
      </div>

      {showDaySelector && (
        <div className="day-selector">
          {days.map((d) => {
            const key = d.toISOString();
            const active = startOfDay(d).getTime() === dayStart.getTime();
            return (
              <button
                key={key}
                className={`day-btn ${active ? "active" : ""}`}
                onClick={() => setSelectedDay(d)}
              >
                <span className="day-name">
                  {isToday(d) ? "Hoy" : format(d, "EEE", { locale: es })}
                </span>
                <span className="day-num">{format(d, "d")}</span>
              </button>
            );
          })}
        </div>
      )}

      {isLoading ? (
        <div className="records-loading">Cargando registros…</div>
      ) : sorted.length === 0 ? (
        <div className="records-empty">Sin registros para este día</div>
      ) : (
        <div className="records-table-wrap">
          <table className="records-table">
            <thead>
              <tr>
                <th>Hora</th>
                <th>Glucosa</th>
                <th>Tendencia</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((r) => {
                const val = r.value_mgdl;
                const status = val > targetHigh ? "high" : val < targetLow ? "low" : "in-range";
                return (
                  <tr key={r.id} className={`record-row ${status}`}>
                    <td className="record-time">
                      {format(new Date(r.timestamp), "HH:mm")}
                    </td>
                    <td className="record-value">
                      <span className={`value-pill ${status}`}>{val}</span>
                      <span className="record-unit">mg/dL</span>
                    </td>
                    <td className="record-trend">
                      {trendArrowSymbol(r.trend_arrow)}
                    </td>
                    <td>
                      <span className={`status-dot ${status}`} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="records-count">
            {sorted.length} registro{sorted.length !== 1 ? "s" : ""}
          </div>
        </div>
      )}
    </div>
  );
}
