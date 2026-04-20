import { useActiveAlert, useCurrentGlucose, useSettings, useUpdateAlertFeedback } from "../hooks/useGlucoseData";

const CONF_LABEL: Record<string, string> = {
  high: "alta",
  normal: "normal",
  low: "baja",
};

interface Props {
  onViewHistory: () => void;
}

export function AlertBanner({ onViewHistory }: Props) {
  const { data: alert, isError } = useActiveAlert();
  const { data: current } = useCurrentGlucose();
  const { data: settings } = useSettings();
  const { mutate: patchFeedback } = useUpdateAlertFeedback();

  if (isError || !alert) return null;

  const isHypo = alert.alert_type !== "hyper";
  const confidence = alert.live_confidence ?? alert.confidence;
  const projectedValue = alert.live_projected_value ?? alert.projected_value;
  const etaMinutes = alert.live_minutes_to_hypo ?? alert.minutes_to_hypo;
  const isDanger = isHypo && confidence === "high";
  const currentValue = current?.value_mgdl ?? alert.triggered_value;
  const threshold = isHypo ? (settings?.target_low ?? 60) : (settings?.target_high ?? 180);
  const alreadyOutOfRange = isHypo ? currentValue <= threshold : currentValue >= threshold;
  const title = alreadyOutOfRange
    ? (isHypo ? "Hipoglucemia en curso" : "Hiperglucemia en curso")
    : `${isHypo ? "Posible hipoglucemia" : "Posible hiperglucemia"} en ~${Math.round(etaMinutes)} min`;
  const subtitle = alreadyOutOfRange
    ? `Glucosa actual: ${currentValue} mg/dL · Proyección: ${projectedValue} mg/dL · Confianza: ${CONF_LABEL[confidence] ?? confidence}`
    : `Proyección: ${projectedValue} mg/dL · Confianza: ${CONF_LABEL[confidence] ?? confidence}`;

  return (
    <div className={`alert-banner ${isDanger ? "alert-banner--danger" : "alert-banner--warn"}`}>
      <div className="alert-banner-body">
        <span className="alert-banner-icon" aria-hidden="true">⚠</span>
        <div className="alert-banner-text">
          <strong>{title}</strong>
          <span className="alert-banner-sub">{subtitle}</span>
        </div>
      </div>
      <div className="alert-banner-actions">
        <button
          className="ab-btn ab-btn-ok"
          onClick={() => patchFeedback({ id: alert.id, feedback: "accurate" })}
        >
          Me salvó
        </button>
        <button
          className="ab-btn ab-btn-false"
          onClick={() => patchFeedback({ id: alert.id, feedback: "false_alarm" })}
        >
          Falsa alarma
        </button>
        <button className="ab-btn" onClick={onViewHistory}>
          Ver historial →
        </button>
      </div>
    </div>
  );
}
