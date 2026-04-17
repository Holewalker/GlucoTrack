import { useState, useEffect } from "react";
import { useSettings, useUpdateSettings } from "../hooks/useGlucoseData";

const SCALE_MIN = 40;
const SCALE_MAX = 320;

function RangeBar({ low, high }: { low: number; high: number }) {
  const span = SCALE_MAX - SCALE_MIN;
  const clampedLow = Math.min(Math.max(low, SCALE_MIN), SCALE_MAX);
  const clampedHigh = Math.min(Math.max(high, SCALE_MIN), SCALE_MAX);
  const belowPct = ((clampedLow - SCALE_MIN) / span) * 100;
  const inPct = (Math.max(0, clampedHigh - clampedLow) / span) * 100;
  const abovePct = 100 - belowPct - inPct;

  return (
    <div className="sp-range-bar" aria-hidden="true">
      <div className="sp-bar-low"    style={{ width: `${belowPct}%` }} />
      <div className="sp-bar-range"  style={{ width: `${Math.max(inPct, 0)}%` }} />
      <div className="sp-bar-high"   style={{ width: `${Math.max(abovePct, 0)}%` }} />
      <div className="sp-marker sp-marker-low"  style={{ left: `${belowPct}%` }} />
      <div className="sp-marker sp-marker-high" style={{ left: `${belowPct + inPct}%` }} />
    </div>
  );
}

export function SettingsPanel() {
  const { data: settings } = useSettings();
  const { mutate, isPending, isSuccess, error } = useUpdateSettings();

  const [low, setLow] = useState<number>(60);
  const [high, setHigh] = useState<number>(140);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (settings) {
      setLow(settings.target_low);
      setHigh(settings.target_high);
    }
  }, [settings]);

  const handleSave = () => {
    if (low <= 0 || high <= 0) {
      setValidationError("Los valores deben ser positivos");
      return;
    }
    if (low >= high) {
      setValidationError("El mínimo debe ser menor al máximo");
      return;
    }
    setValidationError(null);
    mutate({ target_low: low, target_high: high });
  };

  return (
    <div className="settings-panel">
      <h2>Rangos objetivo</h2>

      <RangeBar low={low} high={high} />

      <div className="sp-scale">
        <span>{SCALE_MIN}</span>
        <span>{SCALE_MAX} mg/dL</span>
      </div>

      <div className="sp-inputs">
        <div className="sp-field">
          <span className="sp-field-dot sp-dot-low" />
          <label htmlFor="sp-low">Mínimo</label>
          <div className="sp-input-wrap">
            <input
              id="sp-low"
              type="number"
              value={low}
              min={1}
              max={high - 1}
              onChange={(e) => setLow(Number(e.target.value))}
            />
            <span className="sp-unit">mg/dL</span>
          </div>
        </div>

        <div className="sp-divider" />

        <div className="sp-field">
          <span className="sp-field-dot sp-dot-high" />
          <label htmlFor="sp-high">Máximo</label>
          <div className="sp-input-wrap">
            <input
              id="sp-high"
              type="number"
              value={high}
              min={low + 1}
              max={SCALE_MAX}
              onChange={(e) => setHigh(Number(e.target.value))}
            />
            <span className="sp-unit">mg/dL</span>
          </div>
        </div>

        <button className="sp-save" onClick={handleSave} disabled={isPending}>
          {isPending ? "…" : isSuccess && !validationError ? "✓" : "Guardar"}
        </button>
      </div>

      {validationError && <p className="sp-error">{validationError}</p>}
      {error && !validationError && <p className="sp-error">Error al guardar — intentá de nuevo</p>}
    </div>
  );
}
